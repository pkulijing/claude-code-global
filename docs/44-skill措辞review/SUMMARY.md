# SUMMARY：skill 措辞集中 review（round 44）

## 开发项背景

经约 40 轮迭代，`skills/` 下多个 `SKILL.md`、`rules/` 领域规则、`GLOBAL_AGENTS.md` 宪法都越写越长。这些都是**进 context 的指令性文档**（skill body 触发时整段加载、rules 命中触发条件时被 Read、GLOBAL_AGENTS 每 session 常驻），冗长直接吃 token 预算、稀释关键指令。希望集中 review 一轮、去冗余、精简措辞。

范围初始为「超过 100 行的 5 个 skill」，开发中经用户扩到「所有超过 100 行的进 context 文档」，含 2 份 rules 与宪法本身，共 8 份。

## 实现方案

### 关键设计

1. **借 skill-creator 的 know-how 作精简 rubric**。用户敏锐指出「有 skill-generator 但无 skill-ameliorator」。方案不套 skill-creator 的 eval/benchmark 重流程（那验「功能正确性」，本任务是主观「措辞省不省」），而是把它「Improving the skill」「Writing Style」两节的判据固化成 6 条可操作检查项（DRY / 删演化史 / 压 why / 软化 MUST / progressive disclosure / 表格散文二选一），逐段过。

2. **硬底线：零行为回归**。这些是被真跑/真遵循的可执行指令，删过头会导致行为退化。全程严守「只动措辞与结构、不碰实质规则/分支/踩坑防御」。Plan agent 复核时点名了几处「删过头」风险（`Closes #N` 反例、sync 三态注解、`--bare` 结论半句），据此精准切割。

3. **cross-skill 去重按片段性质二分**（Plan agent 的关键纠正，避免一刀切）：
   - **有单一实现体的契约**（labels helper 的 gh/glab dispatch + exit 降级，散在 3 处约 40 行）→ 下沉到脚本同目录文档 `scripts/platform_issue.md`，3 处各留一句引用。脚本路径本就是 3 处硬编码引用的，引用它旁边的文档零跨软链脆弱性。
   - **纯 AI 步骤片段**（fragment 合并规则、round 顺延、wontfix 手法）→ **不跨 skill 下沉**（跨 skill 引用需穿两条软链的脆弱相对路径），就近各留最简一份。承认 bootstrap（复制语境）与 sync（diff-merge 语境）有细微语境差，硬合并反丢语境。

4. **GLOBAL_AGENTS 孪生化指针提取**（本轮最大单点收益 -48）。5 个领域规则章节各重复「集中维护 + CC 路径 + Codex 路径 + 触发条件」，双端路径提到开头一处、触发条件折叠进汇总表，删掉 44 行重复。机制安全：GLOBAL_AGENTS 单文件软链到两端主文档、同一文本被两端读，故「你在哪端读哪个路径」讲一次零信息损失。

### 开发内容概括

- 新建 2 个下沉文件：`scripts/platform_issue.md`（35 行，labels helper 契约单一真源）、`skills/finish/references/readme-review.md`（24 行，Step 6 下沉，首个用 `references/` 的 skill）。
- 精简 8 份文档，净减 147 行（1895→1748，-7%），**实删字数远超净行数**（多处 3 句压 1 句被 prettier 重排吸收，如 sync -50/+21、python -24/+14）：
  | 文档 | 前→后 | 主要动作 |
  | --- | --- | --- |
  | GLOBAL_AGENTS.md | 161→113 | 孪生化指针提取 |
  | finish | 283→246 | Step 6 下沉、Closes 引用化、labels 引用 |
  | sync-project-config | 374→345 | 三态收敛约定、§2.6 样例压缩、labels 引用 |
  | bootstrap | 249→233 | §3 导言压缩、`--bare` 历史删、labels 引用 |
  | devtree | 220→217 | 完全重建原则复读收敛、Mermaid 防御措辞收紧 |
  | rebase | 141→137 | 各阶段「必停项」收敛为原则 #6 引用 |
  | python.md | 295→285 | §5 打包发布散文压、§3 理由列表压 |
  | ros2.md | 172→172 | §4.6 机理 + §5 导言措辞收紧（被重排吸收） |

### 额外产物

- `docs/44-skill措辞review/PLAN.md`：含 6 条精简 rubric（可直接作为下一轮沉淀 skill 的骨架）+ 各 skill 逐段候选 + 机制约束核实。
- 每个文件落地后的红线自查脚本（grep 校验 fragment 判定 / Closes 反例 / 必停清单 / Mermaid 四防御 / git 署名表等原样保留）。

## 局限性

1. **净行数减幅（-7%）远低于 PLAN 预估（-22%）**。两个真实原因：① 红线比预估密（fragment 迁移判定、Closes 反例、必停清单、Mermaid 防御、ros2 CMake 契约都是「删了出事」的硬内容），严守零行为回归底线故宁少删；② prettier 重排吸收了措辞压缩，实删字数（token 收益）远超净行数。ros2 几乎全是契约（表 + CMake + 14 项 checklist）、devtree 多为产出契约，本就低冗余、压不动是对的。
2. **devtree 的 round42 表格规则尚未压缩**。本 worktree 基于 round42 合入前的 master，worktree 内 devtree 无那 10 行；rebase 吸收 round42 时在冲突解决中把「散文 + blockquote 双讲」压成一段（收尾时处理）。
3. **rubric 只经本轮一次实战验证**，样本是 8 份文档、单人主观判断，尚未证明可稳定复用。

## 后续 TODO

1. **沉淀 `/skill-review`（或 doc-ameliorator）可复用 skill**：本轮已跑通 6 条 rubric + 「按片段性质二分去重」+「progressive disclosure 下沉」。若认可有效，下一轮固化成 skill（范围已含 rules/宪法，故叫 doc-ameliorator 更贴）。避免先造工具后发现 rubric 不对——本轮「先手工跑通」正是为此。
2. **install.sh 重装**：本轮新增 `scripts/platform_issue.md`，`scripts/` 是逐文件软链、需重跑 `bash install.sh` 才软链到 `~/.claude/scripts/`。合并进主 checkout 后执行（skill body 引用的 `$HOME/.claude/scripts/platform_issue.md` 届时才存在）。
3. 剩余可精简空间（若下轮想推进 -15%）：sync 的 fragment 逻辑评估能否安全下沉、python §5 打包整节评估下沉 `rules/references/`。均需逐处确认不伤行为。

## 可沉淀项

本轮就是在 claude-code-global 仓库内做的（自指），无「跨项目资产」需向本仓库跨仓库提 issue。但有一条**本项目可复用资产**值得起 issue 追踪：

- **沉淀 doc-ameliorator skill**（对应后续 TODO #1）：把本轮的 6 条精简 rubric + 二分去重 + progressive disclosure 判据固化成可复用 skill。落点明确（新增 `skills/`），是本仓库自己的正向开发项 → 建议本地 `/backlog` 起 issue。
