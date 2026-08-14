#!/usr/bin/env python3
"""scheduler/install.sh 与 scripts/auto-update.sh 的守护测试。

对应 issue #129：`launchctl unload` 会杀死正在执行它的自己，导致每次成功 pull
之后自动同步彻底停摆。本文件把「不许自杀」与「不许把失败报成成功」钉成回归防线。

设计要点（宪法「环境是被测行为的输入，不是测试环境的属性」）：

- 被测行为在四个环境条件上分叉 —— 是否 Darwin、job 是否已加载、当前进程是否
  跑在 job 内、plist 内容是否有变。四者一律**在用例内显式改写**，各分支各测一遍，
  绝不跟随宿主，也绝不按环境静默跳过。
- 为此 PATH 被收窄成一个**白名单沙盘**：只含本用例显式放进去的工具。于是
  `systemctl` 在「systemd 缺席」用例里是真的不存在，而不是「碰巧这台机器没有」——
  同一份代码在 macOS 与 Linux 上得出逐字相同的结论。
- 假 `launchctl` 精确复刻实测到的真实行为，尤其是 **`load` 无论成败都 exit 0**
  （实测：路径不存在 / plist 损坏 / 重复加载，三种失败模式全部 exit 0）。这正是
  被测代码不能信它退出码的原因，假件必须保真，否则测试会放过真 bug。
- 不发任何网络请求：auto-update 用例的 origin 是本地 bare 仓库。

跑法：python3 docs/58-调度器自杀式重注册/test_scheduler_install.py
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCHEDULER_INSTALL = REPO / "scheduler" / "install.sh"
AUTO_UPDATE = REPO / "scripts" / "auto-update.sh"
LABEL = "com.claude-code-global.auto-update"

# scheduler/install.sh 会用到的真实外部工具。沙盘 PATH 只放这些。
# 缺任何一个都属于「跑测试的前提在这台机器上不存在」，直接报错而非 skip。
NEEDED_TOOLS = [
    "dirname",
    "mkdir",
    "sed",
    "ps",
    "awk",
    "tr",
    "cmp",
    "mktemp",
    "mv",
    "rm",
    "cat",
]

FAKE_LAUNCHCTL = r"""#!/bin/bash
# 假 launchctl：行为按实测复刻（见 docs/58-调度器自杀式重注册/PLAN.md §0）
S="$FAKE_STATE_DIR"
printf '%s\n' "$*" >> "$S/calls.log"
cmd="${1:-}"; shift || true
case "$cmd" in
  list)
    label="${1:-}"
    if [ -z "$label" ]; then
        [ -f "$S/loaded" ] && printf -- '-\t0\t%s\n' "LABEL_PLACEHOLDER"
        exit 0
    fi
    if [ -f "$S/loaded" ]; then
        printf '{\n'
        printf '\t"Label" = "%s";\n' "$label"
        pid="$(cat "$S/pid" 2>/dev/null || true)"
        [ -n "$pid" ] && printf '\t"PID" = %s;\n' "$pid"
        printf '};\n'
        exit 0
    fi
    # 实测：不存在的 label → exit 113
    exit 113
    ;;
  load)
    # 实测：真实 launchctl load 无论成败一律 exit 0，失败信息只在 stderr
    if [ -f "$S/load_ineffective" ]; then
        echo "Load failed: 5: Input/output error" >&2
    else
        : > "$S/loaded"   # 用重定向而非 touch:沙盘 PATH 是白名单,不引入额外依赖
    fi
    exit 0
    ;;
  unload)
    rm -f "$S/loaded"
    exit 0
    ;;
esac
exit 0
"""

FAKE_UNAME = r"""#!/bin/bash
printf '%s\n' "${FAKE_UNAME_S:-Darwin}"
"""


def _resolve_tools():
    resolved = {}
    missing = []
    for tool in NEEDED_TOOLS:
        path = shutil.which(tool)
        if path is None:
            missing.append(tool)
        else:
            resolved[tool] = path
    if missing:
        raise RuntimeError(
            "沙盘缺少必需的外部工具，无法构建可复现的 PATH：" + ", ".join(missing)
        )
    return resolved


class SchedulerInstallTest(unittest.TestCase):
    """scheduler/install.sh 的 macOS / Linux 分支。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ccg-sched-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

        self.home = self.tmp / "home"
        (self.home / ".claude").mkdir(parents=True)
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()

        for tool, real in _resolve_tools().items():
            os.symlink(real, self.bin / tool)

        self._write_exec(
            self.bin / "launchctl", FAKE_LAUNCHCTL.replace("LABEL_PLACEHOLDER", LABEL)
        )
        self._write_exec(self.bin / "uname", FAKE_UNAME)

        self.plist = self.home / "Library" / "LaunchAgents" / f"{LABEL}.plist"

    @staticmethod
    def _write_exec(path: Path, body: str):
        path.write_text(body)
        path.chmod(0o755)

    # ---------- 环境条件的显式改写 ----------

    def set_job_loaded(self, loaded: bool):
        marker = self.state / "loaded"
        if loaded:
            marker.touch()
        elif marker.exists():
            marker.unlink()

    def set_job_pid(self, pid):
        """job 主进程 PID。传本测试进程的 pid 即模拟「我正跑在 job 内」。"""
        (self.state / "pid").write_text(str(pid))

    def set_load_ineffective(self, ineffective: bool):
        """模拟 load 打印 Load failed 却 exit 0、且 job 并未真的起来。"""
        marker = self.state / "load_ineffective"
        if ineffective:
            marker.touch()
        elif marker.exists():
            marker.unlink()

    def run_installer(self, uname_s="Darwin"):
        env = {
            "HOME": str(self.home),
            "PATH": str(self.bin),
            "FAKE_STATE_DIR": str(self.state),
            "FAKE_UNAME_S": uname_s,
            "LC_ALL": "C",
        }
        return subprocess.run(
            ["/bin/bash", str(SCHEDULER_INSTALL)],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def calls(self):
        log = self.state / "calls.log"
        if not log.exists():
            return []
        return [l for l in log.read_text().splitlines() if l.strip()]

    def subcommands(self):
        return [c.split()[0] for c in self.calls() if c.split()]

    def reset_calls(self):
        (self.state / "calls.log").write_text("")

    # ---------- 场景 ----------

    def test_1_首次安装_plist不存在_job未加载(self):
        self.set_job_loaded(False)
        r = self.run_installer()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.plist.exists(), "首次安装必须渲染出 plist")
        self.assertIn("load", self.subcommands(), "首次安装必须真的 load")
        self.assertIn(str(REPO), self.plist.read_text(), "plist 必须完成模板渲染")

    def test_2_内容一致且job已加载_绝不unload(self):
        """★ 主 bug（#129）的回归防线：已是目标状态就什么都别做。"""
        # 先跑一次得到「内容一致」的 plist，再把状态设成 job 已加载
        self.set_job_loaded(False)
        self.run_installer()
        before = self.plist.read_text()
        self.set_job_loaded(True)
        self.set_job_pid(99999999)  # 不在任何 ppid 链上
        self.reset_calls()

        r = self.run_installer()

        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn(
            "unload",
            self.subcommands(),
            "内容一致且已加载时 unload 必须零调用（否则就是自杀路径）",
        )
        self.assertNotIn(
            "load", self.subcommands(), "内容一致且已加载时 load 也不该被调用"
        )
        self.assertEqual(before, self.plist.read_text(), "plist 不该被改写")

    def test_3_内容一致但job掉线_要重新load(self):
        """job 掉线（正是本次故障的残留状态）必须能自愈。"""
        self.set_job_loaded(False)
        self.run_installer()
        self.reset_calls()
        self.set_job_loaded(False)  # 内容一致，但 job 不在

        r = self.run_installer()

        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("load", self.subcommands(), "job 掉线时必须重新 load")

    def test_4_内容有变且不在job内_正常重注册(self):
        self.plist.parent.mkdir(parents=True, exist_ok=True)
        self.plist.write_text("<!-- 旧的、内容不同的 plist -->\n")
        self.set_job_loaded(True)
        self.set_job_pid(99999999)  # 不在本进程的 ppid 链上 → 判定「不在 job 内」

        r = self.run_installer()

        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("旧的", self.plist.read_text(), "plist 必须被更新")
        self.assertIn("unload", self.subcommands(), "不在 job 内时可以正常 unload")
        self.assertIn("load", self.subcommands())

    def test_5_内容有变但正跑在job内_绝不unload(self):
        """★ 自杀防线：确需重注册、但自己正被该 job 承载时，不许就地 unload。"""
        self.plist.parent.mkdir(parents=True, exist_ok=True)
        self.plist.write_text("<!-- 旧的、内容不同的 plist -->\n")
        self.set_job_loaded(True)
        # 本测试进程必然在被测脚本的 ppid 链上 → 判定「我在 job 内」
        self.set_job_pid(os.getpid())

        r = self.run_installer()
        out = r.stdout + r.stderr

        self.assertEqual(r.returncode, 0, out)
        self.assertNotIn(
            "旧的", self.plist.read_text(), "plist 本身仍必须被更新（只是生效时机推迟）"
        )
        self.assertNotIn(
            "unload",
            self.subcommands(),
            "正跑在 job 内时 unload 必须零调用 —— 那会杀死自己",
        )
        self.assertNotIn(
            "load",
            self.subcommands(),
            "同理不该 load（load 前必然要先 unload 才有意义）",
        )
        self.assertIn("登录", out, "必须提示用户重注册推迟到下次登录生效")

    def test_6_load无效时必须报失败(self):
        """★ 第二个 bug 的回归防线：launchctl load 恒 exit 0，不能据此报成功。"""
        self.set_job_loaded(False)
        self.set_load_ineffective(True)

        r = self.run_installer()
        out = r.stdout + r.stderr

        self.assertNotEqual(
            r.returncode, 0, "load 后 job 仍不存在时必须以非零退出，不得误报成功"
        )
        self.assertNotIn("[OK]", out, "不得打印成功提示")

    def test_7_linux且systemd缺席_不碰launchctl(self):
        r = self.run_installer(uname_s="Linux")
        out = r.stdout + r.stderr

        self.assertEqual(r.returncode, 0, out)
        self.assertEqual(self.calls(), [], "Linux 分支不得调用 launchctl")
        self.assertIn("crontab", out, "systemd 缺席时应给出 cron 兜底提示")

    def test_8_非Darwin非Linux_跳过且不报错(self):
        r = self.run_installer(uname_s="FreeBSD")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.calls(), [])


class AutoUpdateInflightTest(unittest.TestCase):
    """scripts/auto-update.sh 的 in-flight 标记（消除静默失败）。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ccg-au-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

        self.agent_home = self.tmp / "agent-home"
        self.agent_home.mkdir()
        self.repo = self.tmp / "repo"
        self.origin = self.tmp / "origin.git"
        self.install_ran = self.tmp / "install-ran"  # install.sh 真跑过的哨兵

        self._git(
            "init", "--bare", "--initial-branch=master", str(self.origin), cwd=self.tmp
        )

        (self.repo / "scripts").mkdir(parents=True)
        shutil.copy(AUTO_UPDATE, self.repo / "scripts" / "auto-update.sh")
        (self.repo / "README.md").write_text("v1\n")
        # install.sh 要在用例里按场景改写(正常收尾 / 中途被硬杀),故必须**不受版本
        # 控制** —— 否则改写它就把工作树弄脏,auto-update.sh 会在 dirty 检查处
        # 直接 skip,根本跑不到 install.sh。
        (self.repo / ".gitignore").write_text("install.sh\n")

        self._git("init", "--initial-branch=master", cwd=self.repo)
        self._git("remote", "add", "origin", str(self.origin), cwd=self.repo)
        self._git("add", "-A", cwd=self.repo)
        self._git("commit", "-m", "init", cwd=self.repo)
        self._git("push", "-u", "origin", "master", cwd=self.repo)

        self._set_installer(self._installer_ok())

    def _installer_ok(self) -> str:
        """正常收尾的 install.sh，并在仓库外留一个「我真的跑了」的哨兵。

        断言取证于这个哨兵而非日志字符串 —— 「日志打印对了而事情没做」正是这类
        脚本最常见的失败形态。
        """
        return f'#!/bin/bash\necho fake-install-ok\necho ran >> "{self.install_ran}"\n'

    def _set_installer(self, body: str):
        p = self.repo / "install.sh"
        p.write_text(body)
        p.chmod(0o755)

    def _git(self, *args, cwd):
        env = dict(os.environ)
        env.update(
            {
                "GIT_CONFIG_GLOBAL": str(self.tmp / "gitconfig"),
                "GIT_CONFIG_SYSTEM": "/dev/null",
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t",
            }
        )
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    def _push_upstream_commit(self):
        """在 origin 上造一个本地没有的新提交，让 auto-update 有东西可拉。"""
        clone = self.tmp / "clone"
        self._git("clone", str(self.origin), str(clone), cwd=self.tmp)
        (clone / "README.md").write_text("v2\n")
        self._git("add", "-A", cwd=clone)
        self._git("commit", "-m", "upstream", cwd=clone)
        self._git("push", "origin", "master", cwd=clone)
        shutil.rmtree(clone)

    def run_auto_update(self, locale="C"):
        # locale 是**被测行为的输入**，不是测试环境的属性：脚本的中文日志行里有
        # `${var}` 紧贴全角字符，而 bash 对它的解析随 locale 分叉（实测 bash 3.2：
        # UTF-8 下裸写 $var 会把全角字符首字节吃进变量名 → 配合 set -u 直接 abort，
        # C locale 下反而无事）。故必须显式指定、各分支各测一遍，绝不跟随宿主。
        env = dict(os.environ)
        env.update(
            {
                "AGENT_HOME": str(self.agent_home),
                "GIT_CONFIG_GLOBAL": str(self.tmp / "gitconfig"),
                "GIT_CONFIG_SYSTEM": "/dev/null",
                "LC_ALL": locale,
                "LANG": locale,
            }
        )
        return subprocess.run(
            ["/bin/bash", str(self.repo / "scripts" / "auto-update.sh")],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    @property
    def inflight(self) -> Path:
        return self.agent_home / ".auto-update-inflight"

    @property
    def stamp(self) -> Path:
        return self.agent_home / ".auto-update-last-run"

    def log_text(self) -> str:
        p = self.agent_home / "logs" / "auto-update.log"
        return p.read_text(errors="replace") if p.exists() else ""

    def test_1_正常同步_标记建了又清掉(self):
        self._push_upstream_commit()
        r = self.run_auto_update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ok: updated to", self.log_text())
        self.assertFalse(self.inflight.exists(), "成功后 in-flight 标记必须被清除")
        self.assertTrue(self.stamp.exists(), "成功后必须写节流戳")

    def test_2_install中途被杀_标记留下且下次告警(self):
        """★ 消除静默失败：本次故障全程无任何异常输出，正是它潜伏两个月的原因。

        两个 locale 各跑一遍：告警行里有 `${var}` 紧贴全角字符，而 bash 对它的
        解析随 locale 分叉。只测一侧的话，「报告崩溃的那一行自己崩掉」这种
        bug 会在另一侧永久失去覆盖 —— 那正是本轮要根除的静默失败形态。
        """
        for locale in ("C", "en_US.UTF-8"):
            with self.subTest(locale=locale):
                self.setUp()  # 每个 locale 用全新的沙盘
                self._push_upstream_commit()
                # 模拟 launchctl unload 的效果：install.sh 把承载它的 auto-update.sh 杀掉
                self._set_installer("#!/bin/bash\nkill -9 $PPID\nsleep 5\n")

                self.run_auto_update(locale=locale)

                self.assertTrue(
                    self.inflight.exists(),
                    "被硬杀之后 in-flight 标记必须留在原地（这是唯一的痕迹）",
                )
                self.assertFalse(self.stamp.exists(), "中途死亡不得写节流戳")

                # 下一次运行必须把这件事说出来
                self.install_ran.unlink(missing_ok=True)
                self._set_installer(self._installer_ok())
                r = self.run_auto_update(locale=locale)

                self.assertNotIn(
                    "unbound variable",
                    r.stdout + r.stderr,
                    "告警行不得因 $var 紧贴全角字符而在 set -u 下崩掉",
                )
                log = self.log_text()
                self.assertIn(
                    "上次的 install.sh 未成功完成",
                    log,
                    "下次运行必须对上次的中途死亡告警",
                )
                self.assertTrue(
                    self.install_ran.exists(),
                    "上次死在 install.sh 里 → 本次必须真的补跑它，"
                    "否则部署会永远停在半截（pull 已完成，走「已是最新」直接退出）",
                )
                self.assertFalse(self.inflight.exists(), "告警后必须清除标记")

    def test_4_标记在提前退出时必须留存(self):
        """补跑机会不许被静默丢掉。

        若检测到标记就立刻清除，那么「检测到 → 却因工作树脏而 bail」这一路
        会把补跑机会悄悄吃掉 —— 而标记恰恰是为根除这类静默失败而加的。
        """
        self.inflight.write_text("1786000000")
        (self.repo / "README.md").write_text("本地脏改动\n")  # tracked 文件 → 工作树脏

        self.run_auto_update()

        self.assertIn("skip: dirty working tree", self.log_text())
        self.assertTrue(
            self.inflight.exists(),
            "提前退出时标记必须原样留存，等阻塞解除后自动补跑",
        )
        self.assertFalse(self.install_ran.exists(), "本次不该跑 install.sh")

        # 阻塞解除 → 下一次必须真的补跑
        self._git("checkout", "--", "README.md", cwd=self.repo)
        self.run_auto_update()

        self.assertTrue(self.install_ran.exists(), "阻塞解除后必须补跑 install.sh")
        self.assertFalse(self.inflight.exists(), "补跑成功后必须清除标记")

    def test_5_install非零退出_标记留存并在下次补跑(self):
        """install.sh 干净地失败（非零退出）与被硬杀，留下的是**同一个洞**。

        两种情形下 `git pull` 都已成功、部署都没做完。若此时清掉标记，下次运行
        会因 LOCAL == REMOTE 走「已是最新」分支直接退出，install.sh 永远不会被
        重跑 —— 机器永久停在半截部署，且日志从下一次起转绿，直到上游出现新提交
        才被顺带修好。
        """
        self._push_upstream_commit()
        self._set_installer("#!/bin/bash\necho 装到一半失败了 >&2\nexit 3\n")

        self.run_auto_update()

        self.assertIn("install.sh exited 3", self.log_text())
        self.assertTrue(
            self.inflight.exists(),
            "install.sh 非零退出时标记必须留存 —— 部署没做完，和被硬杀一样需要补跑",
        )
        self.assertFalse(self.stamp.exists(), "失败不得写节流戳")

        # 下一次运行：LOCAL == REMOTE，只有靠标记才可能触发补跑
        self._set_installer(self._installer_ok())
        self.run_auto_update()

        self.assertTrue(self.install_ran.exists(), "下次运行必须补跑 install.sh")
        self.assertFalse(self.inflight.exists(), "补跑成功后必须清除标记")
        self.assertTrue(self.stamp.exists(), "补跑成功后必须写节流戳")

    def test_6_补跑时保留最初的故障时间(self):
        """标记里的时间戳就是「已经坏了多久」这个信号本身。

        每次补跑都把它覆写成当前时间，日志就会永远显示「上次坏在一小时前」——
        而本轮要根除的那次真实故障，关键信息恰恰是「它已经静默了四天」。
        """
        self._push_upstream_commit()
        original = "1786000000"
        self.inflight.write_text(original)
        self._set_installer("#!/bin/bash\nexit 3\n")

        self.run_auto_update()

        self.assertEqual(
            self.inflight.read_text().strip(),
            original,
            "补跑再次失败后，标记必须仍是最初那次失败的时间戳",
        )

    def test_3_无更新可拉时不建标记(self):
        r = self.run_auto_update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("already up to date", self.log_text())
        self.assertFalse(self.inflight.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
