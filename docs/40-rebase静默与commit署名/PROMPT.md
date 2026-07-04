# PROMPT — round40：/rebase 静默直行 + commit 署名身份

本轮打包两条独立但同属「skill 层体验/正确性」的 P2 issue，一并收敛。

---

## 需求一：`/rebase` 默认静默直行，只在有风险时才停

> 来自 [#41 /rebase 默认静默直行，只在有风险时才停下确认（无冲突 rebase 应近乎瞬间完成）](https://github.com/pkulijing/claude-code-global/issues/41)
> Labels: `type:refactor` `area:skill` `priority:P2`

**动机**：`/rebase` 现在遵循「核心原则 #6 分段确认」——阶段 0 诊断、阶段 1 备份、阶段 2 rebase、阶段 3 FF 合并，**每个阶段结束都停下等人类回 OK**。对一个**无冲突**的 rebase，这意味着 3~4 个「停下 → 回 OK」的 gate，全程拖沓；而无冲突 rebase 本该几乎瞬间完成。

**希望达到**：`/rebase` 默认「静默直行」——诊断、备份、rebase、FF 合并一气呵成，**只在真正有风险 / 需要人类决策时才停下提醒**。无冲突场景近乎瞬间跑完，末尾汇报结果即可。

**方向**（采方向 A）：把「分段确认」从「每阶段必停」改为「风险触发才停」，定义清晰的**必停清单（risk gates）**，不在清单内就继续。

- **停**：分叉方向不明 / 当前分支就是 base；要 rebase 的是 `master`/`main` 或公共分支；工作区不干净；出现冲突；FF `--ff-only` 失败；出现看不懂的状态；**推送到远程**（`--force-with-lease` / 推主干）。
- **不停**：诊断清楚且方向明确、工作区干净、rebase 无冲突、FF 成功 —— 直接跑完。

**硬约束（静默不牺牲安全）**：

- 「数据优先于直线历史」不变；备份 tag **仍必打**（即便静默直行）。
- 冲突 / FF 失败 / 公共分支 / 脏工作区 **仍必停**。
- 推送环节属高影响，即便无冲突也**保留一次确认**，不能静默 force push。
- 措辞调整要同步核心原则 #6 与各阶段「停下确认」的表述，**避免自相矛盾**。

**scope**：小。改 `skills/rebase/SKILL.md` 一处，无代码。

---

## 需求二：Codex 执行提交时使用正确 `Co-authored-by` 身份

> 来自 [#44 fix(commit): Codex 执行提交时使用正确 Co-authored-by 身份](https://github.com/pkulijing/claude-code-global/issues/44)
> Labels（正文待补）: `type:bug` `area:skill` `priority:P2`
> 来源项目：teleop-operator / 来源轮次：docs/32-平台建联评审收敛（跨项目自动沉淀）

**背景**：在 Codex 中执行 `/finish` / `/commit` 收尾时，生成的 commit trailer 仍写了 Claude 身份（`Co-authored-by: Claude <noreply@anthropic.com>`）。本轮实际提交由 Codex 执行，但全局规则与 commit skill 示例偏 Claude，Codex 会自然复用该身份，导致署名与实际 Coding Agent 不一致。

**期望**：

- `/commit` 根据当前执行 agent 选择正确 `Co-authored-by` trailer。
- Codex 执行时不写 Claude 身份。
- 至少在 `GLOBAL_AGENTS.md` 和 `skills/commit/SKILL.md` 给出明确的 Codex/CC 分支规范。

**验收**：

- CC 执行提交仍用 Claude 约定身份。
- Codex 执行提交用 Codex 约定身份（`OpenAI Codex` 或明确的中性身份）。
- 规则文档中说明两个 agent 的署名策略。

**建议落点**：`GLOBAL_AGENTS.md` 的 git 规则 · `skills/commit/SKILL.md` 的 commit message 生成步骤 · `skills/finish/SKILL.md` 中调用 `/commit` 的说明。
