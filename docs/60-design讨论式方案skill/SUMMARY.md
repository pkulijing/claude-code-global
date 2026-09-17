# SUMMARY：新增 `/design` 讨论式方案 skill

## 开发项背景

现有 `/start` → `/finish` 与 `/quick` 都假设需求已经明确。另一类常见需求——只有一段模糊背景、要在多轮讨论中逐步收敛出框架级方案，且方案本身就是产出——没有合适入口：`/start` 要求先有明确 PROMPT 并以执行为目标；CC 的 plan mode 产物不进仓库、不记录讨论过程、退出即执行，长讨论还会被上下文压缩丢掉决策。

## 实现方案

### 关键设计

- **落点 `docs/design/<中文主题>/`，不编号**。不放顶级 `design/`：`docs/design/` 正是理想结构（`docs/design/` + `docs/develop/`）的一半，将来若迁移轮次目录无需再搬；顶级 `design/` 在前端项目里易与设计稿目录撞名。已核实 `/start`、`/commit`、`/finish`、`/rebase`、`/review-loop` 识别轮次都只认 `docs/<数字>-*`，`docs/design/` 不会被误判。
- **两份文件、两种写法**：`DISCUSSION.md` 是历史，只追加（阶段 0 为原样保留的背景输入，之后每阶段记输入 / 分析 / 决策 / 否决，决策即时写入以抵御上下文压缩、支撑 `--resume`）；`DESIGN.md` 是快照，随讨论整体改写，顶部带 `讨论中` / `已定稿` / `已搁置` 状态。不单设 PROMPT —— 多轮讨论里最初的描述没有特殊地位。
- **不是开发轮次**：不占编号、不开 worktree、不进 plan mode、不写代码、不拆 issue、不碰 DEVTREE、不写 SUMMARY。方案可能很宏观、未必落地，故不强制拆 issue；以后落地某部分时由 round 单向引用该 `DESIGN.md`。
- **讨论方法**：默认按「问题定义 → 约束 → 方案空间 → 取舍 → 收敛」推进，每轮只抛 1–2 个带建议的问题，阶段收束时确认；能查的事实自己只读去查，「只有人知道」的问人。
- **用户推翻先前决策记为新决策**，与宪法「自己写错不留痕」区分开。
- **会话中途 `/commit` 存档**，使跨设备续聊可行。

### 开发内容

- 新增 `skills/design/SKILL.md`。
- `GLOBAL_AGENTS.md`：核心开发模式补 `/design` 形态说明；「总结」一步注明对 design 的 SUMMARY 豁免；文档记录规范补 `docs/design/` 例外落点。
- `skills/start/SKILL.md`：需求模糊时指向 `/design`；落地某份 design 时在 `PROMPT.md` 顶部引用。
- `skills/quick/SKILL.md`：前置判断补 `/design` 去向。
- `README.md`：skill 表与导语补 `/design`。
- `install.sh`：入口处硬拦「在 git linked worktree 内运行」，报错并给出主 checkout 下的正确命令，不留开关。从 worktree 跑会把两端全局软链整体改指到 worktree、删除后全部断链，这个坑在 round 31 / 51 / 52 / 53 / 54 里一直靠文档提醒绕开，本轮又实际踩了一次，故改为机制拦截。判定比较 `git-dir` 与 `git-common-dir` 的物理路径（兼容旧版 git，不用 `--path-format`）。验证未合入的 install 改动改走 `CCG_INSTALL_LIB_ONLY` 沙盘。
- `docs/60-*/test-worktree-guard.sh`：守卫的沙盘测试（linked worktree / 主 checkout / 非 git 目录 / 相对路径四种判定 + 直接执行 worktree 副本时退出码非 0、临时 HOME 无副作用、提示命令正确），先跑红再实现。

## 局限性

- `/design` 尚未在真实讨论中跑过，阶段推进与记录粒度是否合适有待实际使用检验。
- 两处边缘场景未处理：上次会话在「先落盘」中途中断导致只有一份文件时，`--resume` 没有补齐步骤；中文主题名未约束 `/` 等路径字符。
- 仅支持仓库内落点，不属于任何仓库的宏观讨论暂无归处。

## 后续 TODO

- 用一次真实讨论试跑 `/design`，据体验调整。
- 若出现「放在哪个仓库都不对」的讨论，再考虑仓库外落点（如 `config.env` 里的 `DESIGN_HOME`）。
- 视需要把轮次目录迁到 `docs/develop/`，与 `docs/design/` 对称（涉及多个 skill 的轮次路径、下游项目历史目录搬迁与文档内相对链接，代价较大）。

## 可沉淀项

暂无（本轮暴露的「worktree 内跑 install.sh」问题已在本轮以 install.sh 守卫解决）。
