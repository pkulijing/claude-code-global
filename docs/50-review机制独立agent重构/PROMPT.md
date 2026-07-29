# PROMPT: review 机制独立 agent 重构

> 来自 [#60 review-loop: /code-review 因 disable-model-invocation 无法被模型调用，主路径与降级链第一档同时不可达](https://github.com/pkulijing/claude-code-global/issues/60)
> Labels: `type:bug` `area:skill` `priority:P0`

## 背景

当前 `/review-loop`（round 45–48 演化而来）的主路径是「委派子 agent 跑 CC 自带 `/code-review`」，降级链第一档是「主会话直跑 `/code-review`」。issue #60（来自 `devops-bot` round16 实战）发现：`/code-review` 被标记 `disable-model-invocation`，**任何模型上下文（子 agent 或主会话）都无法通过 Skill 工具调用它**——主路径与降级第一档同时不可达，按现有文字只能一路滑到「本会话自审」，恰恰丢掉了独立视角，是 skill 明确想避免的最差档。

本轮开轮时的环境实证进一步确认这不是 devops-bot 特例，且**可用性本身在漂移**：

- round 48（本仓，数周前）的 REVIEW.md 记录了委派子 agent 成功跑 `/code-review medium` 的实测数据（两轮 ~32 万 token）——当时可用；
- 本会话（同一台机器、同一仓库）当前的可调用 skill 列表里已**没有** `code-review`（只有 `review`（GitHub PR）与 `security-review`）——现在不可用。

即：`/code-review` 的模型可调用性由 CC 版本 / 会话类型 / plugin 配置等**外部因素**决定，本仓无法控制。把 review 机制的主路径押在这个假设上，等于每次环境漂移都会让门禁静默降级到最差档。

## 用户 intent（本轮评估与重构的准绳）

1. **独立 context**：希望有一个独立 agent（独立的 context，不复用开发 context）做 review；
2. **CC 原生**：不需要来自 codex 等外部模型，CC 自己就行；
3. **全自动**：由开发流程自动化调用，不需要人在环。

## 需求

1. **系统评估**当前 review 机制（`/review-loop` + `/commit` 集成 + 宪法「提交前 review」小节）的问题，以上述三条 intent 为准绳，不限于 issue #60 指出的可达性问题；
2. **重构 `/review-loop`**：使主路径**不依赖「`/code-review` 可被模型调用」这一环境假设**——参考 issue #60 的实战做法（委派子 agent 手工执行 `/code-review` 方法论：N 个并行独立 reviewer + 置信打分去重 + 可执行探针验证，两轮收敛、发现 9 个真实问题，效果已验证）；
3. **同步联动文件**：`skills/commit/SKILL.md` 第 4 步摘要、`GLOBAL_AGENTS.md`「核心开发模式」与「提交前 review」小节，与重构后的 `/review-loop` 保持一致（`/review-loop` 为单一真源）；
4. **处置 issue #60**：本轮收尾 commit 写 `Closes #60`。

## 范围与约束

- 保留 round 47/48 已沉淀且与本次无冲突的机制：收敛三要素并闸（运行验证 + 高置信过滤 + 已定前提）、TDD 正序修复、琐碎跳过判定（指令 / 配置文件不跳）、成本与 diff 规模挂钩、REVIEW.md 留痕；
- 同模型自审盲区的「已知局限」诚实声明保留——intent 2 明确接受 CC 原生、不引外部模型；
- 本轮改动全部是指令 / 规则文档（`skills/*.md`、`GLOBAL_AGENTS.md`），运行验证闸 N/A，但绝不属于「琐碎可跳过」——review 时按指令规则文件对待。

## 待决问题（PLAN 前需人类拍板）

1. **每 2 轮强制人工闸口的去留**：现行硬规则「自动修复每满 2 轮必停下交人」与 intent 3「不需要人在环」存在张力——正常收敛（≤2 轮）确实无人在环，但不收敛时人被拉回环内；云端 routine / 后台会话下「停下问人」会永久挂起。
2. **`/code-review` 依赖的处置**：完全移除（原生方法论为唯一主路径，最简），还是机会主义保留（子 agent 可用清单里有它时优先用，拿上游方法论红利；没有时走原生方法论——即 issue #60 的建议落点）。
