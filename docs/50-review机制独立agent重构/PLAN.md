# PLAN: review 机制独立 agent 重构（Closes #60）

## 背景

`/review-loop` 现行主路径「委派子 agent 跑 CC 自带 `/code-review`」已不可达：`/code-review` 是 CC 内置命令，新版 CC（2.1.220）给它加了 `disable-model-invocation`——任何模型上下文（子 agent 或主会话）都无法经 Skill 工具调用它，仅用户手输可用。实证链：

- round 48（2026-07-10，本仓）：委派子 agent 成功跑 `/code-review medium`，REVIEW.md 留有两轮实测 token 数据——当时可用；
- 本轮开轮（2026-07-29，同一台机器）：模型可调用 skill 列表已无 `code-review`——已不可用；
- devops-bot round16（issue #60）：显式报错 `Skill code-review cannot be used with Skill tool due to disable-model-invocation`。

即主路径与降级第一档（主会话直跑）同废，按现行文字实际每次都会滑到最差档「本会话自审」。

用户 intent（本轮准绳）：① 独立 context 的 agent 做 review（不复用开发 context）；② CC 原生、不引外部模型；③ 开发流程全自动调用、无人在环。

## 系统评估结论

1. **P0 可达性**（issue #60）：主路径 + 降级第一档押在「`/code-review` 可被模型调用」这一不可控、不可观测、已被证实漂移的外部假设上——环境一变，门禁静默降级到最差档。
2. **降级链排序违背 intent ①**：现行降级链为保 `/code-review` 方法论宁可牺牲 context 独立性（主会话直跑），末档「本会话自审」两者全丢——独立 context 应是不可让渡的首要属性。
3. **skill 文本大量逆向描述上游内部实现**（finder 扇出、angle 数、verify 结构、合法/禁止组合）——随 CC 版本静默失效，维护面外溢。
4. **2 轮人工闸口与 intent ③ 冲突**：后台/云端会话下「停下问人」永久挂起。
5. **保留资产**（与本次无冲突）：三要素并闸收敛、TDD 正序修复、琐碎跳过判定、置信过滤、REVIEW.md 留痕、同模型自审盲区诚实声明。

## 关键设计决策（人类已拍板）

- **人工闸口 → 自动放行 + 留痕兜底**：2 轮不收敛即自动停环——剩余 finding 写 REVIEW.md「未收敛遗留」段 + commit message body 加标注行，照常放行 commit；人工兜底天然落在 `/finish`（分支合并前人本来就要过一遍）。无 docs 目录的轮（`/quick`）只落 commit 标注 + 对话告知。token 上限保护不变（至多 2 轮自动修复）。
- **`/code-review` 依赖 → 完全移除**：用户确认「禁止 model invocation = 根本不可用」后落定。原生方法论为唯一主路径；SKILL 保留历史缘由说明（人工手输 `/code-review` 仍可自行使用）。
- **独立 context 优先的降级链**：委派 orchestrator > 主会话结构化自审（显著标注）> 不 review（禁止）。
- **编队两档规格**：默认 3 reviewer（全 sonnet）/ 重档 5 reviewer（深审 opus），复杂特征触发清单沿用现行。

## 重构后的机制设计

### Step 3 选档 →「reviewer 编队规格」

| 档   | 编队                                                | 触发                                                                    |
| ---- | --------------------------------------------------- | ----------------------------------------------------------------------- |
| 默认 | 3 个并行 reviewer，全 `sonnet`                      | 一切需要 review 的改动                                                  |
| 重   | 5 个并行 reviewer，深审角度用 `opus`、其余 `sonnet` | 现行复杂特征清单不变（并发/多线程/跨进程重试/状态机/难复现/跨 3+ 模块） |

成本三硬规则重写：① **范围钉死**——委派 prompt 必须限定「只审 diff 及其接壤代码，禁止全库扫描」（Agent 工具无 effort 入参，成本靠 reviewer 数量 × 模型 × 任务范围约束）；② **永远委派**（独立 context + 主 context 不被文件阅读撑大）；③ **编队只有两档，不自行加码**。

### Step 4 委派 → 独立 review orchestrator

主会话起 1 个 orchestrator 子 agent（`general-purpose`，`model: sonnet`，同步），任务书：

1. 按档位并行起 N 个 reviewer 子 agent，各自独立读 diff、独立产出 finding（file:line + 严重度 + 理由 + 证据）。角度分工（对齐官方 code-review plugin 的多 agent 结构 + devops-bot round16 实战）：默认档 ① 浅层 bug 扫描 ② 契约与装配 ③ 项目规范合规；重档追加 ④ git 历史上下文 ⑤ 并发/状态机/资源生命周期深审（`opus`）。
2. 汇总去重 + 按 0–100 置信 rubric 打分（对齐官方 plugin：0/25/50/75/100，<80 过滤），存疑高分项跑可执行探针（边界值、调用点核对）验证后定分。
3. 返回单一结构化 finding 列表，**不修改任何文件**。
4. 「已定设计前提」清单照旧传入（orchestrator 转传各 reviewer）。
5. **内部兼容**：orchestrator 若无法再起子 agent，则自己按角度清单顺序审并注明——委派与独立 context 仍成立。

### Step 5 降级链重排

1. 委派 orchestrator（主路径）；2. 委派失败（Agent 工具不可用，如 Codex 端）→ 主会话按角度清单**结构化自审** + 置信过滤，顶部显著标注「未经独立 context 把关」；3. 绝不静默跳过。

### 6.4 终止保护改造

「每 2 轮强制人工闸口」→「**2 轮自动上限 + 留痕放行**」。振荡/发散提前停同样走留痕放行。交互会话用户随时可打断，但规则不再主动停下问人。

## 文件改动清单

1. `skills/review-loop/SKILL.md`——核心重构（frontmatter description、为什么存在、Step 3/4/5、6.4、已知局限、明确不做）。
2. `skills/commit/SKILL.md`——第 4 步摘要重写 + 第 7 步补「未收敛标注行」。
3. `GLOBAL_AGENTS.md`——「核心开发模式」段、「需求生命周期·执行」段、「提交前 review」小节；顺带收紧为「机制一句话 + 硬规则点名 + 指向 skill 单一真源」。
4. `README.md`——工作流总述、`/commit` 行、`/review-loop` 行、协作流程段共四处同步。

## 测试用例（指令文档改动，运行验证闸 N/A）

1. **自举 dogfooding**（round 48 同款）：改完后按新 SKILL.md 完整跑一遍 review-loop 审本轮 diff——活体验证 orchestrator 委派、reviewer 扇出可行性、finding 格式、置信过滤与收敛，留痕 `docs/50-*/REVIEW.md`。
2. **孤儿引用检查**：grep 全仓（`docs/` 历史轮除外）`code-review` 引用应仅剩「历史缘由 / 人工手输仍可用」的有意提及。
3. 收尾 `/finish`：SUMMARY.md + DEVTREE，commit 写 `Closes #60`。
