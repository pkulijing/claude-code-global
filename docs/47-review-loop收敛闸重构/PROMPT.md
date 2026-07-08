# PROMPT — review-loop 收敛闸重构

> 来自 [#24 把「codex review 循环」纳入开发生命周期](https://github.com/pkulijing/claude-code-global/issues/24)（本轮为其重开后的重构）
> Labels: `type:feat` `area:skill` `priority:P1`

## 背景

round 45/46 落地 `/review-loop`（commit 前自动引入独立第二模型 codex review 当前 diff、迭代至 clean）。上线后实战暴露两个症状：

1. **开发变慢**：review 总在犄角旮旯挑无关紧要的 corner case，每个小 commit 都背一次全量 codex 迭代。
2. **review 效果差**：某项目连审多轮，最后出来的代码**基础功能都是废的**。

## 调研定位（详见本轮讨论 / issue #24 评论）

问题不在「该不该用 codex」——跨模型独立视角的价值（issue 原始硬实证：grpc.aio 迁线程 codex 补出 3 个 CC 漏判的 P1）依然成立。真正的病根是 **review-loop 的收敛判据设计错了**：

- **收敛闸缺置信过滤**：判据「是否真会出错」没有置信阈值，codex（尤其对规则类文档）问题空间近乎无穷，任何编得出的 corner case 都过闸 → 慢 + 挑刺。对比：anthropic 官方 code-review plugin 用 **0–100 置信分、只留 ≥80**，并显式过滤 pre-existing / pedantic / linter 能抓的。
- **收敛闸没有运行验证**：loop 收敛信号是「codex 说 clean」，而 codex 跑 `read-only` **只读代码、不跑代码**，全程没有任何一步真正运行代码 / 跑测试。于是基础功能在某次 surgical fix 里被改废也无人发现。对比：Karpathy「测试过了才算修好」、Osmani「testing 是最大分水岭」、本仓 rules §3.7「编排器必须有 happy-path integration test」——但 review-loop 没把它接进收敛闸。
- **codex 用法层级错**：把「一次性第二意见」错用成「每 commit 自动无限迭代的收敛裁判」。社区主流是「Claude 规划 + Codex 紧凑第二意见」。

## 本轮目标

重构 `/review-loop`（及必要时的宪法 `GLOBAL_AGENTS.md` 措辞），把收敛闸从「codex 说 clean」改成正确的三要素，让 review 快、准、且不会把基础功能审废：

1. **加运行验证闸**：每轮修复后强制跑受影响测试 + happy-path 主流程，作为收敛的硬前置（呼应 `/verify`、rules §3.7）。
2. **加置信过滤闸**：明确指令 codex 只报「有 file:line 证据、高置信真会在生产触发」的 correctness 问题；编造式 corner case / pre-existing / linter 能抓的 / pedantic 一律不报。
3. **codex 分层**：日常 commit 默认走更快、自带 verification 过滤的 CC `/code-review`；只在并发/复杂/难复现 diff 上引 codex 做一次性第二意见（而非每 commit 无限迭代）。

## 约束

- 本轮改的是**门禁 / 流程自身的规则**（skill + 可能的宪法），属「绝不自动跳过 review」类；改完自身也要走一遍（本轮 review 由人类把关，避免自举无限迭代）。
- 保持双端（CC / Codex）共读一致性：宪法 `GLOBAL_AGENTS.md` 与 `rules/*` 经 install.sh 双轨软链，措辞对两端同等适用。
- 向后兼容：`/commit` 自动调 `/review-loop` 的入口不破坏；降级路径（codex 不可用 → 本会话自审）保留。

## 交付

- 重构后的 `skills/review-loop/SKILL.md`
- 必要时同步 `GLOBAL_AGENTS.md`「独立模型 review」小节措辞
- `docs/47-review-loop收敛闸重构/PLAN.md` + `SUMMARY.md`
