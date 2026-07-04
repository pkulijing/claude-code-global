# SUMMARY — round40：/rebase 静默直行 + commit 署名身份

本轮打包两条独立、同属「skill 层体验 / 正确性」的 P2 issue（#41、#44），纯文档改动、无代码。

## 开发项背景

### #41 — `/rebase` 每阶段必停太拖沓（正向体验优化）

- **希望解决的问题**：`/rebase` 旧的「核心原则 #6 分段确认」要求阶段 0 诊断 / 阶段 1 备份 / 阶段 2 rebase / 阶段 3 FF 合并**每个阶段都停下等人类回 OK**。对一个**无冲突**的 rebase，这就是 3~4 个「停下 → 等 OK」的 gate，全程拖沓 —— 而无冲突 rebase 本该近乎瞬间完成，人类被迫为「零风险」操作反复点头。

### #44 — Codex 收尾提交误写 Claude 署名（BUG）

- **BUG 表现与影响**：在 Codex 中执行 `/finish` / `/commit` 收尾时，生成的 commit trailer 仍写 `Co-authored-by: Claude <noreply@anthropic.com>`。本轮实际提交由 Codex 执行，但全局规则与 commit skill 示例都偏 Claude，Codex 自然复用该身份 → 提交署名与实际 Coding Agent 不一致。来源：teleop-operator 项目 docs/32 轮跨项目沉淀。

## 实现方案

### 关键设计

- **#41 — 风险 gate 模型（方向 A）**：把「每阶段必停」翻转为「**默认静默直行，命中必停清单才停**」。核心原则 #6 内嵌一份**必停清单（risk gates）**作为全篇「何时停」的**单一真源**，各阶段结尾的停顿全部改为「引用必停清单、命中才停」的条件化措辞，消除「原则说静默、阶段仍写必停」的自相矛盾。**安全不打折**是硬约束：备份 tag 无条件必打；脏工作区 / 冲突 / FF 失败 / 公共分支 / **推送**仍必停（绝不静默 force push）；数据优先于直线历史原则不变。
- **#44 — 按执行 Agent 自选身份**：关键洞察是 skill / 规则文档经 `install.sh` **双轨软链**到 `~/.claude/`（CC）与 `~/.codex/`（Codex），**同一份内容被两端共读**，故规则不能写死某一方，必须写成「**按你自己是哪个 Agent 自选**」。判据取 **Agent 的自我身份**（CC 跑 Claude 模型、Codex 跑 GPT 模型，各自 100% 确知自己是谁）—— 这是最可靠的信号，无需探测环境变量 / 路径。配套硬规则「**Codex 绝不写 Claude 身份，CC 绝不写 Codex 身份**」双保险。身份串沿用历史主流（近 20 次提交 14 次的 `Claude`）+ 对称构造 Codex 侧 `OpenAI Codex <noreply@openai.com>`。

### 开发内容概括

| 文件                     | 改动                                                                                             | issue |
| ------------------------ | ------------------------------------------------------------------------------------------------ | ----- |
| `skills/rebase/SKILL.md` | 原则 #6 重写为「默认静默直行 + 必停清单」；阶段 0/1/2/3 停顿全部条件化；push 必停 + 末尾结果汇报 | #41   |
| `GLOBAL_AGENTS.md`       | git 规则 `Co-authored-by` 由单示例改为 CC/Codex 分支表格 + 判据 + 硬规则                         | #44   |
| `skills/commit/SKILL.md` | 第 8 步硬编码 Claude → 按 Agent 自选身份两分支                                                   | #44   |
| `skills/finish/SKILL.md` | Step 7 补一句：委托 `/commit` 按 Agent 选身份，Codex 收尾不写 Claude                             | #44   |

### 额外产物

- 无独立测试 / 脚本（skill 指令文档无可执行测试面）。以两条 grep 自查替代：① rebase 停/确认/静默措辞审查（确认无「分段确认 / 每阶段必停」残留、原则 #6 与各阶段一致）；② 三处署名一致性审查（CC/Codex 两分支齐备、身份串一致）。均通过。

## 局限性

- **#44 身份判据依赖 Agent 自我认知**，非环境探测。实践中 Claude 模型不会误认自己是 Codex、反之亦然，故可靠；但若未来出现「CC 里跑非 Claude 模型」等非常规组合，判据措辞（「CC 跑 Claude 模型」）会略失精确。当前不为这种边缘情形加环境探测，保持规则简单。
- **#44 Codex 身份串 `OpenAI Codex <noreply@openai.com>` 是对称构造**，非 OpenAI 官方钦定；若日后 Codex 有官方 trailer 约定，需回来对齐。
- **#41 是纯措辞契约**，靠 Agent 遵守文档执行；无 harness 层强制。措辞已尽量把「必停清单」写成单一真源以降低跑偏概率。

## 后续 TODO

- 观察 Codex 端实跑 `/commit` / `/finish` 是否确实按新规则写 `OpenAI Codex` 身份（本轮由 CC 执行，Codex 分支未实测）。
- 若 `/rebase` 静默直行在真实无冲突 rebase 上体验良好，可考虑把同款「风险 gate」模型推广到 `/finish` Step 8 的 worktree 收尾措辞（目前 8.2 仍写「停下等用户确认」）。

## 可沉淀项

- **`/finish` Step 8 worktree 收尾也可套用同款「风险 gate 静默直行」**：本轮把 `/rebase` 的「每阶段必停」翻转为「风险才停」，`/finish` Step 8.2/8.3 目前仍是「rebase 无冲突也停下等用户确认」，属同类拖沓。**去向：跨项目资产（改 `skills/finish/SKILL.md`）**，但当前仓库即 claude-code-global，按自指守卫走**本地 `/backlog`**，不跨仓 file。已在「后续 TODO」记录，是否起 issue 交用户定。
