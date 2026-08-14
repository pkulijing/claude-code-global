# PLAN：修复自动同步调度器的自杀式重注册

对应需求见同目录 `PROMPT.md`（issue [#129](https://github.com/pkulijing/claude-code-global/issues/129)）。

## 〇、外部行为断言实证

PROMPT 里对 launchctl 行为的断言全部先跑沙盘验过再定设计，结论如下。复现命令与探针脚本见本文末「附录：探针复现」。

| # | 断言 | 实测结论 |
| --- | --- | --- |
| A1 | `launchctl unload` 会杀死正在执行它的自己 | **成立**。沙盘 job 的日志停在 `[E] 即将 unload`，其后的 `[F]` 从未打印，job 也从 `launchctl list` 消失 —— 与生产日志的断点形态逐字一致 |
| A2 | `launchctl list <label>` 可抽出 job 主进程 PID | **成立**。输出 plist-ish dict，含 `"PID" = <n>;`，`awk` 可稳定抽取 |
| A3 | ppid 链上溯能在**三层嵌套**下认出「我在 job 内」 | **成立**。launchd 报告的是最外层 `auto-update.sh` 的 PID；`scheduler/install.sh` 的链 `80616 → 80612 → 80607` 命中 |
| A4 | `launchctl load` 的退出码可用来判成败 | **不成立，且是个独立的 bug** —— 见下 |
| A5 | `launchctl list <label>` 的退出码可用来判存在性 | **成立**。存在 → 0，不存在 → **113** |
| A6 | 新式 `bootstrap` / `bootout` 的退出码是否可信 | **可信**（坏路径 → 5，不存在 → 3），与 legacy 相反 |

### A4 展开：本轮顺带挖出的第二个 bug

`launchctl load` 在**所有**失败模式下都返回 **exit 0**：

| 失败模式 | stderr | exit |
| --- | --- | --- |
| plist 路径不存在 | `Load failed: 5: Input/output error` | **0** |
| plist 语法损坏 | `Load failed: 5: Input/output error` | **0** |
| job 已加载（重复 load） | `Load failed: 5: Input/output error` | **0** |

而现有代码 `scheduler/install.sh:53-60` 恰恰用它的退出码判成败，并且 `2>/dev/null` 把唯一的失败信号（stderr）也吞了：

```bash
if launchctl load -w "$plist_dst" 2>/dev/null; then   # ← 恒真
    success "已注册 launchd 调度器(登录跑 + 每小时跑)"
else
    warn "launchctl load 失败,可手动: ..."             # ← 死代码，永远进不去
    return 1
fi
```

**结论：注册失败会被报成绿色的成功。** 这正是宪法 wrapper 原则里「失败怎么向外传 —— 假设错了它会一直报成功」那条的实例。本轮一并修掉：**成败判据改为事后查询 `launchctl list` 的退出码**（A5），不再信 `load` 的返回值。

> 附带影响：本轮不迁移到 `bootstrap` / `bootout`（A6）。它们退出码可信，但 `-w` 的 enable 语义要拆成单独的 `launchctl enable`，改动面与回归面都更大；用 `launchctl list` 验证同样拿得到真判据，且对老系统兼容性更宽。留作备选，记在「局限性」里。

## 一、方案选型

采 issue 里的**方案 A**（真幂等 + 在 job 内检测），并一并做**方案 C**（消除静默失败）。放弃方案 B（plist 注入哨兵变量）—— 它有先有鸡问题：引入哨兵本身要改 plist 内容，从而触发一次重注册，存量机器仍会再自杀一次。

**方案 A 是自交付的**：`auto-update.sh` 先 `git pull` 再跑 `install.sh`，所以拉到修复的那一次运行执行的已经是**新版** `scheduler/install.sh`；而存量机器的 plist 内容与渲染结果一致、job 也已加载，恰好命中新增的早退分支 → 当场不再自杀。无需用户手动做任何事。

## 二、改动设计

### 2.1 `scheduler/install.sh` — `install_macos()` 重写

新增三个 helper（仅 macOS 分支使用）：

```bash
LABEL="com.claude-code-global.auto-update"

# job 是否已加载：launchctl list <label> → 0 存在 / 113 不存在（实证 A5）
job_is_loaded() { launchctl list "$LABEL" >/dev/null 2>&1; }

# job 主进程 PID（未运行时为空）（实证 A2）
job_pid() {
    launchctl list "$LABEL" 2>/dev/null \
        | awk -F'= ' '/"PID"/{gsub(/[^0-9]/,"",$2); print $2}'
}

# 当前进程是否跑在该 job 内 —— ppid 链上溯（实证 A3）
running_inside_job() {
    local jp p
    jp="$(job_pid)"; [ -n "$jp" ] || return 1
    p=$$
    while [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null; do
        [ "$p" = "$jp" ] && return 0
        p="$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')"
    done
    return 1
}
```

主流程改为四路分支：

```
渲染 plist 到临时文件 tmp
│
├─ ① tmp 与已装 plist 内容一致  且  job 已加载
│     → 已是目标状态，info 一句，直接 return 0     ★ 主 bug 的修复点
│
├─ ② 需要重注册  且  running_inside_job
│     → 只把 tmp 落到 plist_dst，warn「已更新 plist，但当前正由该 job 运行，
│        重注册推迟到下次登录生效；如需立即生效可在终端手动跑 <命令>」
│     → return 0（不算失败：plist 已更新，语义完整，只是生效时机推迟）
│
├─ ③ 需要重注册  且  不在 job 内（人工 `bash install.sh` / 首次安装）
│     → 落 plist，launchctl unload（忽略错误）+ launchctl load -w
│     → **用 job_is_loaded 验证**，通过才 success；不通过 warn + return 1  ★ A4 的修复点
│
└─ ④ 找不到 launchctl（理论上非 Darwin 才会，防御性）
      → warn + return 1
```

「需要重注册」= plist 内容有变 **或** job 未加载。两者取或 —— 内容没变但 job 掉了（正是本次故障的残留状态）也必须重新 load。

### 2.2 `scripts/auto-update.sh` — 消除静默失败

本次故障**全程无任何异常输出**，这是它潜伏两个月的真正原因。加一道不依赖信号语义的 in-flight 标记：

- 调 `install.sh` **之前**：`echo "$NOW" > "$AGENT_HOME/.auto-update-inflight"`，内容为时间戳。
- `install.sh` 正常返回后：删除该文件。
- **脚本启动时**：若该文件存在 → `log "warn: 上次运行在 install.sh 中途异常终止（<时间>），本次将重试"`，然后删除它继续跑。

为什么不用 `trap`：launchd 卸载时先 SIGTERM 后 SIGKILL，落在 SIGKILL 上时 trap 不执行；标记文件法不依赖收到哪个信号，任何形式的中途死亡都留痕。

**节流戳 `.auto-update-last-run` 的写入时机不动** —— 它的语义是「成功完成一次同步」，提前写会让失败的运行在 30 分钟内不重试，是语义倒退。

### 2.3 不动的部分

- `scheduler/launchd.plist.template`：**一个字节都不改**。改了就会让存量机器的 plist 内容比对失配，从而在修复生效前先触发一次重注册（也就是再自杀一次）。这是方案 A 自交付性质的前提。
- Linux 分支的调度语义：`systemctl --user disable --now <timer>` 停的是 timer 单元，正在跑的 `Type=oneshot` service 不会被带走，不存在对称问题。仅补一条测试钉住「Linux 分支不调用 launchctl」。
- `install.sh` 主体：不改。

## 三、测试计划（TDD，先红后绿）

`scheduler/` 目前零单测，本轮新建 `docs/58-调度器自杀式重注册/test_scheduler_install.py`（放置位置沿用 round 52 的 `test_context_budget.py` 先例），用 python3 + `subprocess` 驱动真实的 `scheduler/install.sh`。

**隔离手段（产品代码零改动即可测）**：

- `HOME=<tmpdir>` —— 隔离 `plist_dst`（`$HOME/Library/LaunchAgents/...`）与 `AGENT_HOME` 探测；
- `PATH=<fakebin>:$PATH` —— 放入假的 `launchctl` 与 `uname`。

**按宪法「环境是被测行为的输入，不是测试环境的属性」**，以下条件一律在用例内显式改写、各分支各测一遍，**不跟随宿主、不按环境 skip**：

- `uname -s` 的返回值（`Darwin` / `Linux`）→ 假 `uname`；
- job 是否已加载 → 假 `launchctl` 的 `list` 子命令返回 0 或 113；
- 「是否在 job 内」→ 假 `launchctl list` 吐出的 PID：命中场景吐**测试进程自身的 PID**（必然在被测脚本的 ppid 链上），未命中场景吐 `999999`；
- `load` 是否真的生效 → 假 `launchctl` 按脚本化状态机应答。

假 `launchctl` 同时把每次调用**追加记录到调用日志**，用例据此断言「哪些子命令被调过、哪些没被调过」—— 场景 2 的核心断言正是 `unload` **一次都没被调用**。

| # | 场景（显式设定的环境） | 断言 |
| --- | --- | --- |
| 1 | Darwin / plist 不存在 / job 未加载 | 渲染出 plist；调了 `load`；退出 0 |
| 2 | Darwin / plist 内容一致 / job 已加载 | **`unload` 与 `load` 均零调用**；plist 未被改写；退出 0 ★ 主 bug 回归防线 |
| 3 | Darwin / plist 内容一致 / job 未加载 | 调了 `load`；退出 0（掉线的 job 要能自愈） |
| 4 | Darwin / plist 内容有变 / 不在 job 内 | plist 被更新；调了 `unload` + `load`；退出 0 |
| 5 | Darwin / plist 内容有变 / **在 job 内** | plist 被更新；**`unload` 零调用**；输出含推迟提示；退出 0 ★ 自杀防线 |
| 6 | Darwin / 需注册 / `load` 后 `list` 仍报 113 | **退出非 0** 且输出含失败提示 ★ A4 回归防线（现有代码此处误报 success） |
| 7 | Linux / systemctl 缺席 | 不调用任何 `launchctl`；给出 cron 兜底提示；退出 0 |

另补一条 `scripts/auto-update.sh` 的 in-flight 标记用例：预置残留标记文件 → 断言日志出现 warn 行且标记被清除。

**先写测试跑出红**（场景 2、5、6 必红），再改实现转绿。

## 三·五、执行中的设计调整（相对上面已确认的计划）

两处，都是实现过程中被证据推着改的，记在这里而非直接改写原文，以便 review 时看得见转向。

### 调整 1：in-flight 标记从「只报警」升级为「报警 + 补跑闸」

原计划（§2.2）只让下次运行打一行 warn。写完测试才发现这个设计有洞：**上次死在
`install.sh` 里时，`git pull` 往往早已成功**，于是下一次运行走「已是最新」分支直接退出，
`install.sh` 永远不会补跑 —— 部署停在半截，要等到下次有新提交才被顺带修好。日志里那句
「本次将重试」纯属虚言。

改法：检测到残留标记时置 `FORCE_INSTALL=1`，让「已是最新」那条路也补跑一次
`install.sh`（它本身幂等）。为此把原本散在末尾的 install 段抽成
`run_install_and_finish()`，两条路径共用。

**标记检测的位置也随之刻意后移**到所有 skip 分支之后、真正动手之前，并且**不在检测时清除
标记**（只在 `run_install_and_finish` 里清）。否则「检测到 → 清掉 → 却因工作树脏 / fetch
失败而 bail」会把补跑机会静默吃掉 —— 与本轮要根除的失败形态是同一类。

### 调整 2：locale 成为显式的测试维度

按 `playbooks/shell.md` §2 自查时发现 `log "…（$PREV_HUMAN），…"` 里
`$var` 紧贴全角括号，配合本脚本的 `set -u` 会让**报告崩溃的那一行自己崩掉**。已改为
`${PREV_HUMAN}`。

顺带一个与 playbook 记载相反的实测：该 playbook 说这坑出现在「非 UTF-8 locale（C /
POSIX）」，而 bash 3.2 上实测**恰好相反** —— `LC_ALL=C` 正常，`LC_ALL=en_US.UTF-8`
才报 `unbound variable`：

```console
$ LC_ALL=C          /bin/bash -uc 'V="x"; echo "终止（$V），重试"'   # → 终止（x），重试
$ LC_ALL=en_US.UTF-8 /bin/bash -uc 'V="x"; echo "终止（$V），重试"'  # → V?: unbound variable
```

（`${var}` 定界这条修法本身两侧都成立，不受影响。playbook 的措辞待另行更正，记在本轮
SUMMARY 的后续 TODO 里。）

更要紧的是**测试原本把 `LC_ALL` 钉死在 `C`**，正好落在安全的那一侧 —— 这本身就是宪法
「环境是被测行为的输入」的违例：被测行为随 locale 分叉，测试却只测了一支。已把 locale
提为显式维度，`test_2` 经 `subTest` 在 `C` 与 `en_US.UTF-8` 各跑一遍。

## 四、风险与回归面

| 风险 | 缓解 |
| --- | --- |
| 早退分支判错 → 该注册时没注册 | 「需要重注册」取「内容有变 **或** job 未加载」的**或**，任一为真都走注册；场景 3 专测「内容一致但 job 掉线」 |
| `ps -o ppid=` 在极端情况下取不到 → 误判「不在 job 内」→ 又自杀 | 失败方向定死在保守侧：`job_pid` 为空即 `return 1`（视作不在 job 内）会导致自杀 —— 故**顺序上先做①的早退**，①命中就根本走不到检测；检测只在「内容确实变了」这条罕见路径上兜底 |
| 首次安装回归（plist 不存在时必须能注册） | 场景 1 专测 |
| `launchctl list` 的 113 语义在其它 macOS 版本上不同 | 只用「退出码是否为 0」判存在性，不硬编码 113 |
| 存量机器拿到修复前先自杀一次 | 不改 plist 模板 → 内容比对必然一致 → 命中早退（见 §2.3） |

## 五、验收标准

1. 场景 1–7 单测全绿；先红后绿的过程在 commit 历史中可见。
2. 在本机做一次**端到端真机验证**：构造 `origin/master` 领先本地的状态，由 launchd 触发一次真实同步，验证同步完成后 `launchctl list` 中 job **仍在**、节流戳被写入、日志出现 `ok: updated to`（这是全日志里第二次出现该行 —— 第一次还是 2026-06-28）。
3. `bash install.sh` 人工跑一次，调度器注册行为与改动前一致（幂等、不报错）。

## 附录：探针复现

沙盘脚本位于本轮 scratchpad（不入库），核心复现步骤：

```bash
# A1：写一个 plist 注册 job，其脚本内容为
#   echo "[E] before unload" >> log
#   launchctl unload <自己的 plist> >> log 2>&1
#   echo "[F] after unload"  >> log      # ← 观察这行是否出现
launchctl load -w probe.plist && sleep 5 && cat probe.log   # [F] 不出现即断言成立

# A4：launchctl load 的退出码
launchctl load -w /nonexistent/nope.plist; echo "exit=$?"   # 打印 Load failed，exit=0

# A5：launchctl list 的退出码
launchctl list com.claude-code-global.auto-update >/dev/null 2>&1; echo $?  # 0
launchctl list com.nonexistent.nope             >/dev/null 2>&1; echo $?  # 113
```
