#!/usr/bin/env python3
"""`scripts/context_budget.py` 的单测。

零第三方依赖，标准库 unittest。跑法（仓库根目录）：

    python3 -m unittest discover -s docs/52-指令面精简与定期化 -p 'test_*.py' -v

沿用 round51 `docs/51-rules按需加载/test-unlink-legacy.sh` 的「轮次内测试脚本」先例。
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "context_budget.py"

_spec = importlib.util.spec_from_file_location("context_budget", SCRIPT)
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)


class TestEstimateTokens(unittest.TestCase):
    """token 估算。

    这里**不测算术**（那只是复述实现），测的是两件真事：① 估算值贴合 `/context` 的
    实测标定点；② 中文与非中文分桶计。原因见 `scripts/context_budget.py` 模块
    docstring —— 按英文经验值 4 字符/token 估中文会低估约 3 倍。
    """

    # /context 实测（2026-07-31, claude-opus-5）：文件 → token。
    # **内容钉在实测那一刻的 commit 上**，不读工作树 —— 否则本轮把这两个文件改小之后，
    # 标定测试会跟着变红，而变的是被测内容、不是估算模型。
    CALIBRATION_REF = "38d3441"
    CALIBRATION = {"GLOBAL_AGENTS.md": 8000, "CLAUDE.md": 3600}

    def test_empty(self):
        self.assertEqual(cb.estimate_tokens(""), 0)

    def test_cjk_costs_more_tokens_per_char_than_ascii(self):
        self.assertGreater(cb.estimate_tokens("汉" * 100), cb.estimate_tokens("a" * 100))

    def test_additive_across_buckets(self):
        self.assertEqual(
            cb.estimate_tokens("汉" * 124 + "a" * 400),
            cb.estimate_tokens("汉" * 124) + cb.estimate_tokens("a" * 400),
        )

    def test_cjk_punctuation_counts_as_cjk(self):
        # 全角标点在 CJK 区间内，本仓中文正文里占比不低，漏算会系统性低估
        self.assertEqual(cb.estimate_tokens("，" * 100), cb.estimate_tokens("汉" * 100))

    def test_matches_measured_calibration_points(self):
        """回归标定：估算值须落在 /context 实测值 ±5% 内。"""
        for rel, measured in self.CALIBRATION.items():
            with self.subTest(file=rel):
                text = cb.file_at_ref(REPO_ROOT, self.CALIBRATION_REF, rel)
                self.assertIsNotNone(text, f"标定 ref {self.CALIBRATION_REF} 取不到 {rel}")
                est = cb.estimate_tokens(text)
                self.assertGreater(est, measured * 0.95)
                self.assertLess(est, measured * 1.05)


class TestGlobMatch(unittest.TestCase):
    """`*` 不得跨 `/`。

    `delta` 的新侧走 `Path.glob`、旧侧走 `git ls-tree` + 本函数，两侧口径必须一致；
    用 `fnmatch` 会让旧侧多收 `skills/a/b/SKILL.md` 这类嵌套路径，算出假的增长率 ——
    而 delta 正是 `/routine-slim` 是否动手的闸。
    """

    def test_star_does_not_cross_slash(self):
        self.assertFalse(cb._glob_match("skills/a/b/SKILL.md", "skills/*/SKILL.md"))

    def test_star_matches_single_segment(self):
        self.assertTrue(cb._glob_match("skills/commit/SKILL.md", "skills/*/SKILL.md"))

    def test_literal_dots_are_escaped(self):
        self.assertFalse(cb._glob_match("playbooks/pythonXmd", "playbooks/*.md"))

    def test_exact_pattern(self):
        self.assertTrue(cb._glob_match("GLOBAL_AGENTS.md", "GLOBAL_AGENTS.md"))
        self.assertFalse(cb._glob_match("x/GLOBAL_AGENTS.md", "GLOBAL_AGENTS.md"))


class TestExtractRefs(unittest.TestCase):
    """从 markdown 里抽出「可判定的」跨文件引用。

    **零误报是硬要求**：一屏误报会让人干脆不看这个检查，那就等于没有。所以只认精简
    动作真正会产出的那几种指针形态，其余一律不抓。下面的「不该抓」用例全部来自在真实
    仓库上跑出来的误报，逐条钉住。
    """

    def test_picks_backticked_relative_path(self):
        self.assertIn("playbooks/python.md", cb.extract_refs("见 `playbooks/python.md` 一节"))

    def test_picks_home_anchored_path(self):
        # ~/.claude/* 是本仓的软链投影，须归一回仓库内路径
        self.assertIn("scripts/platform_issue.md",
                      cb.extract_refs("契约见 `~/.claude/scripts/platform_issue.md`"))

    def test_maps_global_repo_prefix_to_repo_root(self):
        self.assertIn("playbooks/python.md",
                      cb.extract_refs("见 `~/.claude/global-repo/playbooks/python.md`"))

    def test_maps_user_claude_md_to_constitution(self):
        self.assertIn("GLOBAL_AGENTS.md", cb.extract_refs("全局 `~/.claude/CLAUDE.md` 里写着"))

    def test_picks_shared_template_doc(self):
        self.assertIn("templates/MECHANICS.md", cb.extract_refs("机制见 `templates/MECHANICS.md`"))

    def test_ignores_globs(self):
        # `playbooks/*.md` 是模式不是路径，检查它必然误报
        self.assertEqual(cb.extract_refs("改 `playbooks/*.md` 后"), [])

    def test_ignores_placeholders(self):
        self.assertEqual(cb.extract_refs("留痕到 `docs/<N>-*/REVIEW.md`"), [])
        self.assertEqual(cb.extract_refs("落 `templates/<stack>/__root__/`"), [])

    def test_ignores_prose_without_slash(self):
        self.assertEqual(cb.extract_refs("跑 `git status` 看一眼"), [])

    def test_ignores_urls(self):
        self.assertEqual(cb.extract_refs("见 `https://github.com/owner/repo/issues/1`"), [])

    def test_ignores_paths_outside_repo(self):
        # 运行期产物 / 用户端文件，不在仓库里
        self.assertEqual(cb.extract_refs("写 `/tmp/distill-1.md`"), [])
        self.assertEqual(cb.extract_refs("装到 `.git/hooks/pre-commit`"), [])
        self.assertEqual(cb.extract_refs("读 `~/.claude/settings.json`"), [])

    def test_ignores_commands_and_sample_output(self):
        """带空格的是命令或 git diff 示例输出，不是路径。"""
        self.assertEqual(cb.extract_refs("逃生舱：`bash scheduler/uninstall.sh`"), [])
        self.assertEqual(cb.extract_refs("形如 `A templates/_common/__root__/x.md`"), [])
        self.assertEqual(cb.extract_refs("跑 `git rm docs/BACKLOG.md`"), [])

    def test_ignores_paths_containing_shell_variables(self):
        self.assertEqual(cb.extract_refs("读 `$GLOBAL_DIR/.github/labels.yml`"), [])

    def test_ignores_consumer_project_paths(self):
        """skill 正文里谈的大多是**消费方项目**的文件，不是本仓的。"""
        for prose in ("落 `src/`", "写 `.vscode/settings.json`", "删 `docs/BACKLOG.md`",
                      "装 `node_modules/`", "落 `frontend/`", "模板里 `__root__/`"):
            with self.subTest(prose=prose):
                self.assertEqual(cb.extract_refs(prose), [])

    def test_ignores_intentional_historical_mentions(self):
        """`rules/` 是被刻意保留的历史提法（已改名 playbooks），不是失效指针。"""
        self.assertEqual(cb.extract_refs("曾用名 `rules/`，因撞上保留目录名而改名"), [])

    def test_dedupes(self):
        refs = cb.extract_refs("`playbooks/python.md` 与 `playbooks/python.md`")
        self.assertEqual(refs.count("playbooks/python.md"), 1)


class TestCheckRefs(unittest.TestCase):
    """失效引用检出 —— 「只允许搬走不允许蒸发」的机械兑现。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "playbooks").mkdir()
        (self.root / "playbooks" / "python.md").write_text("# py", encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def test_reports_broken_ref(self):
        (self.root / "skills" / "demo" / "SKILL.md").write_text(
            "细节见 `playbooks/ghost.md`", encoding="utf-8"
        )
        broken = cb.check_refs(self.root)
        self.assertEqual([b.ref for b in broken], ["playbooks/ghost.md"])
        self.assertEqual(broken[0].source, "skills/demo/SKILL.md")

    def test_accepts_existing_ref(self):
        (self.root / "skills" / "demo" / "SKILL.md").write_text(
            "细节见 `playbooks/python.md`", encoding="utf-8"
        )
        self.assertEqual(cb.check_refs(self.root), [])

    def test_resolves_bare_references_dir_relative_to_owning_skill(self):
        """`references/x.md` 是相对 skill 目录写的，不能按仓库根解析。"""
        (self.root / "skills" / "demo" / "references").mkdir()
        (self.root / "skills" / "demo" / "references" / "detail.md").write_text("d", encoding="utf-8")
        (self.root / "skills" / "demo" / "SKILL.md").write_text(
            "按 `references/detail.md` 执行", encoding="utf-8"
        )
        self.assertEqual(cb.check_refs(self.root), [])

    def test_real_repo_has_no_broken_refs(self):
        """在真实仓库上必须零失效引用 —— 这是本轮「搬走而非蒸发」的机械闸。"""
        self.assertEqual([f"{b.source} → {b.ref}" for b in cb.check_refs(REPO_ROOT)], [])


class TestCollectAndMeasure(unittest.TestCase):
    """扫描面与分类：常驻 vs 懒加载，决定了「省了什么」怎么算。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "skills" / "demo" / "references").mkdir(parents=True)
        (self.root / "playbooks").mkdir()
        (self.root / "templates").mkdir()
        (self.root / "GLOBAL_AGENTS.md").write_text("宪" * 100, encoding="utf-8")
        (self.root / "CLAUDE.md").write_text("项" * 50, encoding="utf-8")
        (self.root / "skills" / "demo" / "SKILL.md").write_text("技" * 200, encoding="utf-8")
        (self.root / "skills" / "demo" / "references" / "d.md").write_text("细" * 30, encoding="utf-8")
        (self.root / "playbooks" / "python.md").write_text("py" * 40, encoding="utf-8")
        (self.root / "templates" / "MECHANICS.md").write_text("机" * 60, encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def test_classifies_resident_vs_lazy(self):
        report = cb.measure(self.root)
        by_path = {e.path: e for e in report.entries}
        self.assertEqual(by_path["GLOBAL_AGENTS.md"].category, "resident")
        self.assertEqual(by_path["CLAUDE.md"].category, "resident")
        self.assertEqual(by_path["skills/demo/SKILL.md"].category, "lazy")
        self.assertEqual(by_path["playbooks/python.md"].category, "lazy")

    def test_counts_skill_references_and_shared_docs(self):
        paths = {e.path for e in cb.measure(self.root).entries}
        self.assertIn("skills/demo/references/d.md", paths)
        self.assertIn("templates/MECHANICS.md", paths)

    def test_totals_add_up(self):
        report = cb.measure(self.root)
        self.assertEqual(report.total_chars, sum(e.chars for e in report.entries))
        self.assertEqual(report.resident_chars, 150)

    def test_ignores_unrelated_template_files(self):
        (self.root / "templates" / "python-uv").mkdir()
        (self.root / "templates" / "python-uv" / "README.md").write_text("x" * 999, encoding="utf-8")
        paths = {e.path for e in cb.measure(self.root).entries}
        self.assertNotIn("templates/python-uv/README.md", paths)


class TestDelta(unittest.TestCase):
    """与历史版本对比。无状态：基线从 git 历史算，不落基线文件、不打 tag。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        self._env = env
        self._git("init", "-q", "-b", "main")
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "GLOBAL_AGENTS.md").write_text("宪" * 100, encoding="utf-8")
        (self.root / "skills" / "demo" / "SKILL.md").write_text("旧" * 100, encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        self.base = self._git("rev-parse", "HEAD").strip()

    def _git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], env=self._env,
                              capture_output=True, text=True, check=True).stdout

    def test_growth_detected(self):
        (self.root / "skills" / "demo" / "SKILL.md").write_text("旧" * 300, encoding="utf-8")
        d = cb.delta(self.root, self.base)
        self.assertEqual(d.old_chars, 200)
        self.assertEqual(d.new_chars, 400)
        self.assertAlmostEqual(d.growth_ratio, 1.0, places=3)

    def test_new_file_counts_as_pure_growth(self):
        (self.root / "playbooks").mkdir()
        (self.root / "playbooks" / "new.md").write_text("新" * 50, encoding="utf-8")
        d = cb.delta(self.root, self.base)
        self.assertEqual(d.old_chars, 200)
        self.assertEqual(d.new_chars, 250)

    def test_deleted_file_counts_as_shrink(self):
        (self.root / "skills" / "demo" / "SKILL.md").unlink()
        d = cb.delta(self.root, self.base)
        self.assertEqual(d.new_chars, 100)
        self.assertLess(d.growth_ratio, 0)

    def test_renamed_file_is_net_zero(self):
        """rules/ → playbooks/ 那种改名不该被当成「涨了一倍」。"""
        (self.root / "playbooks").mkdir()
        (self.root / "skills" / "demo" / "SKILL.md").rename(self.root / "playbooks" / "moved.md")
        d = cb.delta(self.root, self.base)
        self.assertEqual(d.new_chars, d.old_chars)
        self.assertAlmostEqual(d.growth_ratio, 0.0, places=6)

    def test_resolve_since_ref_defaults_to_history(self):
        ref = cb.resolve_since_ref(self.root, None)
        self.assertTrue(ref)
        self.assertTrue(cb.file_at_ref(self.root, ref, "GLOBAL_AGENTS.md") is not None)

    def test_file_at_ref_returns_none_for_missing(self):
        self.assertIsNone(cb.file_at_ref(self.root, self.base, "playbooks/nope.md"))


class TestCli(unittest.TestCase):
    """三个子命令在真实仓库上跑得通（冒烟）。"""

    def _run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              cwd=str(REPO_ROOT), capture_output=True, text=True)

    def test_measure_json(self):
        import json
        r = self._run("measure", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertIn("total_chars", data)
        self.assertGreater(data["total_chars"], 0)

    def test_check_refs_exit_code_reflects_findings(self):
        r = self._run("check-refs")
        self.assertIn(r.returncode, (0, 1), r.stderr)

    def test_unknown_subcommand_fails(self):
        self.assertNotEqual(self._run("bogus").returncode, 0)


if __name__ == "__main__":
    unittest.main()
