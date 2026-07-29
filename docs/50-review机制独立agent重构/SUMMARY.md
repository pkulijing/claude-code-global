# SUMMARY: review 机制独立 agent 重构

## 开发项背景

针对 BUG（issue #60，P0）：`/review-loop` 的主路径「委派子 agent 跑 CC 自带 `/code-review`」不可达——新版 CC（2.1.220）给该内置命令加了 `disable-model-invocation`，任何模型上下文（子 agent、主会话）都无法经 Skill 工具调用，仅用户手输可用。主路径与降级第一档（主会话直跑）同废，按旧文字实际每次都滑到最差档「本会话自审」——恰恰丢掉独立视角，是 skill 明确想避免的结果。

影响面：每个 `/commit` 的提交前门禁静默降级；且该 flag 随 CC 版本漂移、不可观测（本仓 round 48 于 2026-07-10 委派成功且有实测数据，数周后同一台机器已不可用；devops-bot 环境从来没有）。

本轮同时以用户三条 intent 为准绳对 review 机制做系统评估：① 独立 context 的 agent 做 review（不复用开发 context）；② CC 原生、不引外部模型；③ 开发流程全自动调用、无人在环。

## 实现方案

### 关键设计

- **根因**：主路径押在「`/code-review` 可被模型调用」这一不可控、不可观测、已被证实漂移的外部假设上。事实核查还厘清一层：磁盘上官方 marketplace 的 `code-review` 插件（`disable-model-invocation: false`）是另一个东西——PR 专用、走 `gh pr comment` 且未安装；带档位、审工作树 diff 的 `/code-review` 是 CC 内置命令，flag 随 CLI 版本走。
- **决策一（用户拍板）：完全移除 `/code-review` 依赖**，不做「环境可用时优先调它」的机会主义保留——本次 P0 的成因模式（上游语义静默漂移）会持续存在。方法论由 skill 自持：委派**独立 context 的 review orchestrator 子 agent**，按档位并行扇出 3 个（默认，全 sonnet）/ 5 个（并发/难复现等硬 diff，深审角度 opus）独立 reviewer 角度，跨 reviewer 去重 + 0–100 置信 rubric 打分（<80 过滤，rubric 对齐官方 plugin）+ 探针验证，返回单一 finding 列表。
- **决策二（用户拍板）：人工闸口改「2 轮自动上限 + 留痕放行」**——不收敛即停环，剩余 finding 写 REVIEW.md「未收敛遗留」段 + commit message 加标注行后照常放行，人工兜底前移到 `/finish`。治「后台/云端会话下停下问人会永久挂起」，token 上限保护不变。
- **决策三：降级链按「独立 context 优先」重排**：委派 orchestrator > 主会话结构化自审（按角度清单 + 置信过滤，显著标注）> 不 review（禁止）。旧「主会话直跑 `/code-review`」档随依赖移除消亡。
- **成本三硬规则重写**：范围钉死（只审 diff 及接壤代码，禁止全库扫描）/ 永远委派 / 编队两档不加码；对上游内部实现的逆向描述（finder 扇出、angle 数、合法组合）全删，消掉一层随版本静默失效的维护面。

### 开发内容概括

- `skills/review-loop/SKILL.md` 核心重构（Step 3 选档=编队规格、Step 4 orchestrator 任务书、Step 5 降级链、6.4 终止保护；三要素并闸 / TDD 正序 / 琐碎跳过判定等 round 47/48 资产原样保留）；
- 联动同步：`skills/commit/SKILL.md`（第 4 步摘要 + 第 7 步未收敛标注行）、`GLOBAL_AGENTS.md` 三处（顺带瘦身、指向 skill 单一真源）、`README.md` 四处。

### 额外产物

- `REVIEW.md`：新机制自举实测——orchestrator 成功嵌套扇出 3 个 reviewer（Agent-in-Agent 可行）、首轮 0 条 ≥80 finding、~11.7 万 token 收敛 clean（对比 round 48 旧路径单轮 ~17 万）；
- `/code-review` 可调用性漂移的完整实证链（round 48 实测数据 ↔ 本会话 skill 列表 ↔ devops-bot 报错），沉淀在 PROMPT/PLAN；
- 顺带逮到并修复又一处 Agent 工具 schema 漂移坑：模板里的 `run_in_background` 参数已被移除（round 48 逮到漏 `description`，同源问题），模板降格为「要点示意 + 按环境实际 schema 填参」。

## 局限性

- **同模型自审盲区仍在**：独立的是 context 而非模型（用户明确接受，intent ②）；grpc.aio 跨模型实证继续作为「已知局限」保留，跨模型第二意见仍是人工逃生舱。
- **重档（5 reviewer 含 opus 深审）未实测**：本轮 diff 是纯指令文档、走默认档，重档成本无实测数据（round 48 的同款遗留顺延）。
- **嵌套扇出依赖环境**：orchestrator 起子 agent 的能力（Agent-in-Agent）并非处处可用，受限环境退化为 orchestrator 顺序审（SKILL 已内置该降级并要求注明）。
- **未收敛留痕放行**意味着高置信遗留问题可能随 commit 进分支——可见性靠 REVIEW.md + commit 标注 + `/finish` 人工兜底三层保证，但不再有阻断闸。
- 2 条低置信 nit 未修（宪法「本端」vs SKILL「主会话」措辞——实为有意区分；「本节只留骨架」自我定性），见 REVIEW.md。

## 后续 TODO

- 实测重档编队（5 reviewer + opus 深审）的真实成本，补上数据缺口；
- reviewer 角度清单随实战演化（如安全专项、性能专项作为重档可选角度）；
- 若未来 CC 恢复 `/code-review` 的模型可调用性，重新评估是否值得引回（当前判断：自持方法论已覆盖其价值且不受漂移影响，倾向不回退）。

## 可沉淀项

本仓即 claude-code-global——本轮改的就是跨项目资产本身（`/review-loop` skill + 宪法 + `/commit`），改动落地即完成沉淀，无需另行提炼。其余暂无。
