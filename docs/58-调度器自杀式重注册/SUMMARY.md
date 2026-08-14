# SUMMARY：修复自动同步调度器的自杀式重注册

对应 issue [#129](https://github.com/pkulijing/claude-code-global/issues/129)（`type:bug` / `area:install` / `priority:P0`）。

## 开发项背景

**表现**：`launchctl list` 里 `com.claude-code-global.auto-update` 整个消失，多设备自动同步彻底停止，直到下次登录（`~/Library/LaunchAgents/` 在登录时被重新加载）才恢复一次。实测 2026-08-10 16:26 → 08-14 10:56 连续四天零运行。macOS 独有。

**影响**：自动同步是全局配置（宪法 / skills / playbooks / agents / templates）跨设备一致性的唯一保障。它停摆时，本机的 Coding Agent 会一直用着旧规则，而这件事**没有任何提示** —— 用户是靠「感觉又不对劲了」才发现的。

**为什么潜伏了两个月**：三重掩护叠在一起。① 只有真拉到更新时才会跑 `install.sh`，没更新时走 `already up to date` 直接退出，平时观察一切正常；② 失效窗口是「拉到更新那刻 → 下次登录」，登录够频繁时它自己就好了，只有赶上连续几天没重新登录才暴露成一次显眼的长时间失效；③ 失败**全程静默**，日志里连一行异常都没有。

**根因**：`auto-update.sh → install.sh → scheduler/install.sh` 这条链由 launchd 拉起时，`scheduler/install.sh` 里那句 `launchctl unload "$plist_dst"` 卸载的正是**承载着这条链本身**的那个 job。launchd 会终止该 job 名下全部进程，于是执行 unload 的 shell 当场被杀、下一行 `load -w` 永远执行不到，job 从此不存在。

三条独立佐证：5 次自杀的日志输出逐字断在同一位置（调度器注册之前），无 `安装完成`、无 `error: install.sh exited`（那是错误路径，会 warn 后继续）—— 是被杀不是报错；全日志 6 次 `pulling` 只有第一次（彼时 job 尚未注册）走到 `ok: updated to`，此后由 launchd 拉起且有更新可拉的运行 **5 次全死**；节流戳停在 08-10 15:26，而 16:26 那次 pull 明明已改变 HEAD。

## 实现方案

### 关键设计

**先实证再设计。** 动手前用最小 launchd 沙盘把四条外部行为断言全跑了一遍（PLAN §0），其中一条推翻了原假设并直接挖出第二个 bug。这一步的成本约十分钟，省掉的是把错误假设写进代码和测试后再返工。

**1 · `scheduler/install.sh`：四路分支取代无条件 unload/load**

| 分支 | 条件 | 行为 |
| --- | --- | --- |
| ① | plist 内容一致 **且** job 已加载 | 什么都不做，早退 ★ 主修复点 |
| ② | 需重注册 **且** 正跑在该 job 内 | 只更新 plist，重注册推迟到下次登录 ★ 自杀防线 |
| ③ | 需重注册 **且** 不在 job 内 | 正常 unload + load，**再查 `launchctl list` 验证** |
| ④ | 找不到 `launchctl` | warn + 非零返回 |

「需重注册」= plist 内容有变 **或** job 未加载（取或，任一为真都走注册 —— 内容没变但 job 掉线，正是本次故障的残留状态，必须能自愈）。

「是否在 job 内」靠 ppid 链上溯：实测 launchd 报告的是最外层 `auto-update.sh` 的 PID，而 `scheduler/install.sh` 是它的孙进程，链上必然命中。

**2 · 同一函数里的第二个 bug：失败被报成绿色的成功**

实证发现 `launchctl load` 在**所有**失败模式下都返回 exit 0（路径不存在 / plist 损坏 / 重复加载，三者都只在 stderr 打印 `Load failed: 5`）。而原代码正是用它的退出码判成败：那个 `if` 恒真、`else` 是永远进不去的死代码，`2>/dev/null` 还把唯一的失败信号也吞了。改为**事后查询 `launchctl list` 的退出码**（实测：存在 → 0，不存在 → 113）。

这是宪法 wrapper 原则里「失败怎么向外传 —— 假设错了它会一直报成功」那条的又一个实例。

**3 · 修复是自交付的**

`auto-update.sh` 先 `git pull` 再跑 `install.sh`，所以拉到修复的那一次执行的已经是**新版**代码；而存量机器的 plist 内容与渲染结果一致、job 也已加载，恰好命中分支 ①，当场不再自杀，用户零操作。

**前提是不动 plist 模板** —— 改了就会让内容比对失配，在修复生效前先自杀一次。故本轮对 `scheduler/launchd.plist.template` 一个字节都没改。已在本机做只读验证：渲染结果与已装 plist 逐字节一致、`launchctl list` 退出码为 0，两条都为真 ⇒ 必然走早退分支。

**4 · `scripts/auto-update.sh`：in-flight 标记消除静默失败**

`install.sh` 跑之前落一个标记，**只有它成功完成才清除**。于是被硬杀与干净的非零退出都会留痕，下一次运行既能报警也能据此补跑。

三个非显然的决定：

- **不用 `trap`**：launchd 卸载时可能直接 SIGKILL，trap 不执行；而这里要防的恰恰是被强杀。
- **标记检测的位置压到所有 skip 分支之后**、真正动手之前，且**不在检测时清除**。放在开头会让「检测到 → 清掉 → 却因工作树脏 / fetch 失败而 bail」把补跑机会静默吃掉 —— 与本轮要根除的失败形态是同一类。
- **时间戳只在首次落标记时写**。补跑路径下保留**最初**那次失败的时间：「已经坏了多久」正是本轮要恢复的信号（上次故障静默了四天），每次补跑都覆写成当前时间等于把它抹掉。

为此把原本散在末尾的 install 段抽成 `run_install_and_finish()`，正常 pull 后与补跑两条路径共用。

### 额外产物

- **`test_scheduler_install.py`（14 条）** —— `scheduler/` 此前零单测。用 python3 驱动真实 bash 脚本，**产品代码零改动即可测**：`HOME=<tmpdir>` 隔离落点，`PATH` 收窄成**白名单沙盘** + 假 `launchctl` / `uname`。
  白名单 PATH 是刻意的：让 `systemctl` 在「systemd 缺席」用例里**真的不存在**，而不是「碰巧这台机器没有」—— 同一份代码在 macOS 与 Linux 上得出逐字相同的结论。假 `launchctl` 精确复刻实测行为（尤其 `load` 恒 exit 0），假件失真就会放过真 bug。
  三条是回归防线：场景 2（内容一致 + 已加载 → `unload` 零调用）、场景 5（在 job 内 → `unload` 零调用）、场景 6（load 无效 → 必须非零退出）。
- **PLAN §0 的沙盘探针**（复现命令记在 PLAN 附录，脚本本身在 scratchpad 不入库）。
- **`REVIEW.md`** —— 两轮 review 的完整留痕，含被丢弃项及丢弃理由。

### 过程中的两次自我修正

都不是外部指出的，记下来因为它们各自代表一类容易重犯的错：

1. **给一个机制加职责后，没回头复查依赖旧职责的判断。** in-flight 标记从「只报警」升级为「补跑闸」之后，`install.sh` 非零退出就清标记那行的理由（「非零退出有自己的日志行」）已经失效，而我没同步更新 —— 于是只堵了硬杀那一支，干净失败那一支反而被主动清掉了标记。第 1 轮 review 抓到（置信 80）。
2. **测试把环境条件钉死在了安全的一侧。** 按 `playbooks/shell.md` 自查时发现 `$PREV_HUMAN` 紧贴全角括号，配合 `set -u` 会让**报告崩溃的那一行自己崩掉**；但测试原本把 `LC_ALL` 固定为 `C`，恰好落在不触发的一侧。这本身就是宪法「环境是被测行为的输入」的违例。已把 locale 提为显式测试维度、两侧各测一遍。

## 局限性

- **真机端到端验证尚未执行。** 这是 PLAN 验收标准里唯一没兑现的一条：它必须在合入 master 后从**主 checkout** 跑，不能在 worktree 里做 —— `install.sh` 会把 `~/.claude/` 下所有软链重指到 worktree 路径，而该 worktree 收尾即删。已做的是只读验证（渲染一致性 + job 加载态），自交付这条链是通的，但「由 launchd 触发一次真实同步、确认 job 存活」还欠一次。
- **同模型自审。** 两轮 review 的 reviewer 与写这份 diff 的同为 Claude 模型家族，独立的是 context 而非模型。本轮涉及进程生命周期与状态机，正是该盲区最大的地方；已按规程升重档（含 `code-reviewer-deep`）缓解，但不等于消除。
- **`FORCE_INSTALL` 补跑闸只挂在「已是最新」分支。** 若同时叠加 non-fast-forward（本地有未推提交）等持久性阻塞，标记会长期留存而补跑不执行，直到阻塞人工解除。判为期望行为（此时仓库根本无法同步，不该硬部署），review 中置信 60、已丢弃。
- **未迁移到 `launchctl bootstrap` / `bootout`。** 它们的退出码可信（坏路径 → 5，不存在 → 3），比 legacy 的恒 0 好；但 `-w` 的 enable 语义要拆成单独的 `launchctl enable`，改动面与回归面更大。本轮用 `launchctl list` 事后验证同样拿到了真判据。
- **Linux 分支未做等价加固。** 已确认不存在对称问题（`systemctl --user disable --now <timer>` 停的是 timer 单元，正在跑的 `Type=oneshot` service 不会被带走），仅补了一条「Linux 分支不碰 launchctl」的测试。

## 后续 TODO

1. **合入后补做真机端到端验证**：构造 `origin/master` 领先本地，由 launchd 触发一次真实同步，确认同步后 job 仍在、节流戳被写入、日志出现 `ok: updated to` —— 那将是全日志里第二次出现这行（上一次是 2026-06-28）。
2. **更正 `playbooks/shell.md` §2 的触发条件描述**（详见「可沉淀项」）。
3. `scheduler/uninstall.sh` 本轮未审视，是否有同类自杀路径未知（它本就要卸载 job，语义上是期望的，但由 launchd 拉起时的行为没验证过）。

## 可沉淀项

本仓即 claude-code-global，按 `/finish` Step 3.3 自指守卫，以下**不自动 file**，建议用 `/backlog` 起本地 issue。

1. **`playbooks/shell.md` §2 的触发条件与实测相反（建议提 issue，`type:docs` / `area:doc` / P2）。**
   该节称 `$var` 紧贴 CJK / 全角字符的坑出现在「**非 UTF-8 locale**（C / POSIX，CC 的 Bash 工具常处于此）」，但 bash 3.2 实测恰好反过来：

   ```console
   $ LC_ALL=C           /bin/bash -uc 'V="x"; echo "终止（$V），重试"'   # 正常
   $ LC_ALL=en_US.UTF-8 /bin/bash -uc 'V="x"; echo "终止（$V），重试"'   # V?: unbound variable
   ```

   修法（一律写 `${var}`）不受影响，但**触发条件写反了会让人按错误方向排查**，也会误导「我这里是 UTF-8，应该没事」的判断。落点明确：§2 那段括号内的措辞。

2. **「测试把环境条件钉死在安全的一侧」值得作为实证补进宪法（建议提 issue，`type:docs` / `area:doc` / P2）。**
   宪法「环境是被测行为的输入」一节已有一条实证（真发网络请求导致 16s vs 120s，一直绿着所以潜伏很久）。本轮是**另一种形态**：环境条件被显式写死了，只是恰好写死在不触发的那一侧 —— 比「跟随宿主」更隐蔽，因为它看起来完全符合「显式指定环境」的要求，评审时不会觉得可疑。判据可补一句：**显式指定环境之后还要问一句「另一侧测了吗」**。落点：宪法「测试先行」段那一节。

3. **`launchctl load` 恒 exit 0 是 wrapper 原则「失败怎么向外传」的第三个实例。** 宪法该条已有两个方向相反的实证（「以为它没有其实有」「以为它有其实要显式开」），本轮这个属于第二类，**已被现有条文覆盖**，不必再加 —— 记在这里只为说明该条文确实在反复命中，暂无需改动。
