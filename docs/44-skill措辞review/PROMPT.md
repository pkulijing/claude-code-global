# PROMPT：skill 措辞集中 review

## 背景

经过约 40 轮迭代，`skills/` 下多个 skill 的 `SKILL.md` 越写越长。长 skill 里难免积累：

- **冗余表述**：同一约束在多处重复叮嘱；
- **过度展开的历史注释**：`round-XX` / 旧版对比 / 「踩过的坑」的来龙去脉铺得过细；
- **过度纠结细节的措辞**：把「why」和「what」都摊开写，句子可无损压缩。

这些对**上下文空间是严重浪费**——skill body 在 skill 触发时整段进 context，冗长直接吃掉 token 预算、也稀释真正的关键指令。

## 需求

集中 review 一轮 skill 措辞，产出精简。

### 范围

**超过 100 行的「进 context 的指令性文档」都参与本轮 review**，短的先不看。不止 skill —— `rules/` 领域规则与 `GLOBAL_AGENTS.md` 宪法同样每次进 context，冗余成本一致，一并纳入：

- **skills**：`sync-project-config`（374）/ `finish`（283）/ `bootstrap`（249）/ `devtree`（~230，含 round42 表格规则）/ `rebase`（141）。
- **rules**：`python.md`（295）/ `ros2.md`（172）。
- **宪法**：`GLOBAL_AGENTS.md`（161）。
- 100 行及以下本轮不动：skills（`start` 98 / `pybump` 98 / `paper-read` 87 / `quick` 85 / `backlog` 85 / `commit` 38）、rules（`frontend` 69 / `lark` 33 / `shell` 33）。

### review 方法

借用 `skill-creator`（skill-generator）的 know-how。它没有对称的「精简 / ameliorate 现有 skill」能力，但其「Improving the skill」「Writing Style」两节沉淀了一套「什么是好 skill」的判据，恰好可作为精简 rubric：

1. **Keep it lean**——删掉不 pulling weight 的重复表述；
2. **别堆 MUST / ALWAYS / NEVER**——僵硬全大写是 yellow flag，应改写为解释 why；
3. **Explain the why, not just the what**——但已过度展开的 why 要收敛；
4. **Progressive disclosure**——SKILL.md body 里的细节能下沉到 `references/` 就下沉、可重组结构。

这是**偏主观、以人类判断为准**的质量维度，故**不套** skill-creator 的 eval/benchmark 重流程（那套验「功能正确性」，非「措辞省不省」）。

## 关键约束与决策（已与用户确认）

1. **产出形态**：先对 5 个 skill 各产一份「冗余点清单 + 建议改法」，用户集中 review 拍板后再统一落地。不边 review 边改。
2. **精简力度**：**中等**——除删冗余外，允许把 body 细节下沉到 `references/`、允许重组结构（progressive disclosure），不止于删字。
3. **不改变行为语义**：精简只动措辞与结构，**所有实质规则、分支逻辑、踩坑防御、`why` 的核心必须保留**。这是硬底线——skill 是会被真跑的可执行指令，删过头会导致行为退化。
4. **本轮不沉淀 skill**：先手工按 rubric 跑通、验证 rubric 有效；若用户认可，作为「后续 TODO」记进 SUMMARY，下一 round 再固化成 `/skill-review`（或 ameliorator）这类可复用 skill。避免先造工具后发现 rubric 不对。

## 验收

- 5 个 skill 各有一份可 review 的精简清单（冗余点 + 建议改法 + 预估省下的行数/token）；
- 用户拍板后按认可项落地，落地后每个 skill 行为语义不变、仅措辞/结构精简；
- SUMMARY 记录 rubric 有效性判断 + 「是否沉淀成 skill」的后续 TODO。
