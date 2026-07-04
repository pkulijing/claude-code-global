# PLAN — round40：/rebase 静默直行 + commit 署名身份

两条 issue 各自独立、落点不重叠，可并行改。均为 skill / 规则**文档**改动，无代码、无可执行单测；验收靠「文档内部自洽 + 无自相矛盾措辞」（#41 issue 明确警示这点）。

---

## 需求一（#41）：`skills/rebase/SKILL.md` 改为「风险 gate」模型

**唯一改动文件**：`skills/rebase/SKILL.md`。四处联动改，确保「默认静默直行」与各阶段措辞一致、不自相矛盾。

### 1.1 核心原则 #6：`分段确认` → `风险 gate（默认静默直行）`

把第 6 条从「每阶段必停」重写为「默认静默直行、命中必停清单才停」，并**内嵌必停清单**（risk gates），作为全篇「何时停」的单一真源：

> 6. **默认静默直行，风险才停（risk gates）**：诊断方向明确且无风险时，诊断 → 备份 → rebase → FF 合并**一气呵成、不逐阶段等确认**，末尾汇报结果。**仅在命中下列「必停清单」时停下、说明原因、等人类决策**：
>    - 分叉方向不明 / 诊断看不清；
>    - 当前分支就是 base（如无参时在 `master`）；
>    - 要 rebase 的是 `master` / `main` 或已被 review 的公共分支（呼应原则 #3）；
>    - 工作区不干净；
>    - rebase 出现**冲突**；
>    - FF `git merge --ff-only` 失败；
>    - 需**推送到远程**（`--force-with-lease` 或推主干）——高影响，即便无冲突也停一次确认，绝不静默 force push；
>    - 任何看不懂 / 意外的状态。
>      不在清单内（方向明确、工作区干净、rebase 无冲突、FF 成功）→ 直接继续，不打断人类。

安全不打折：原则 #4「数据优先于直线历史」不变；备份 tag（阶段 1）**无条件必打**，静默直行也不例外。

### 1.2 阶段 0 结尾：条件化「等确认」

现「诊断报告中明确写出……**停下来等人类确认后进入阶段 1**」→ 改为：

> 诊断报告中明确写出「将把 `<current>` rebase 到 `<base>`」。**若方向明确且未命中必停清单（§ 核心原则 #6），直接进入阶段 1，无需等确认**；若方向不明 / 当前分支即 base / 目标是公共分支等命中必停项，停下说明原因等人类决策。

### 1.3 阶段 1 结尾：条件化「等确认」

- 保留强制项：工作区必须干净（不干净 = 命中必停）、**打备份 tag（无条件）**、切分支。
- 现「**停下来等人类确认后进入下一阶段。**」→ 改为：

> 工作区干净时，打完备份 tag 直接进入阶段 2；**工作区不干净则停下**要求人类先 commit / stash。

### 1.4 阶段 2 结尾：无冲突静默续，有冲突才停

- 「若无冲突」分支：现「直接展示 `git log` 让人类肉眼验证，然后进入阶段 3」→ 改为「无冲突则展示 `git log --graph --oneline -10` 备查后**直接进入阶段 3，不停顿**」。
- 「若有冲突」分支末尾「**停下来等人类确认历史正确后进入下一阶段。**」→ 改为「**冲突属必停项**：解决过程与解决后都停下让人类过目、确认历史正确再进入阶段 3」。

### 1.5 阶段 3：FF 静默续，push 必停

- FF 合并：`--ff-only` 成功 → 直接继续；**失败则停**（回阶段 2 续 rebase，仍禁 fallback 普通 merge）。
- 推送：**推送前必停一次确认**（`--force-with-lease` / 推主干都属高影响），措辞明确「即便前面全程无冲突，push 仍需人类点头」。
- 末尾：静默直行跑完后给一份**结果汇报**（做了哪些阶段、备份 tag 名、当前 graph、是否需 push）。

> 净效果：无冲突 + 无需 push 的 rebase = 阶段 0→1→2→3 一路无停顿，末尾一次汇报；有风险处（脏区 / 冲突 / FF 失败 / 公共分支 / push）精准停。

---

## 需求二（#44）：commit `Co-authored-by` 按执行 Agent 自选身份

**核心机制**：skill / 规则文档经 `install.sh` 双轨软链到 `~/.claude/`（CC）与 `~/.codex/`（Codex），**同一份内容被两端读取**，故规则必须写成「**按你自己是哪个 Agent 自选**」——判据是 Agent 的**自我身份**（CC 跑 Claude 模型、Codex 跑 GPT 模型，各自 100% 确知自己是谁），这正是 issue 要求的「明确的 CC/Codex 分支规范」，且是最可靠的信号（无需探测 env / 路径）。

**身份约定**（沿用历史主流 + 对称构造）：

| Agent                 | trailer                                             |
| --------------------- | --------------------------------------------------- |
| CC（Claude Code）     | `Co-authored-by: Claude <noreply@anthropic.com>`    |
| Codex（OpenAI Codex） | `Co-authored-by: OpenAI Codex <noreply@openai.com>` |

> CC 侧沿用近 20 次提交里 14 次的主流写法 `Claude`；Codex 侧对称构造 `OpenAI Codex <noreply@openai.com>`。硬规则：**Codex 绝不写 Claude 身份、CC 绝不写 Codex 身份**。

### 2.1 `GLOBAL_AGENTS.md` git 规则（真源）

把「由 AI 协助完成的提交，commit message 末尾必须包含 `Co-authored-by` trailer，例如 `Claude Sonnet`」改为**按 Agent 分支的表格 + 判据 + 硬规则**（内容如上表 + 「你知道自己是哪个 Agent，据此选；Codex 绝不写 Claude 身份」）。

### 2.2 `skills/commit/SKILL.md` 第 8 步

现硬编码 `Co-authored-by: Claude <noreply@anthropic.com>` → 改为「按当前执行 Agent 选 trailer（见全局 CLAUDE.md『git 规则』）」并列出 CC / Codex 两分支 + 「Codex 绝不写 Claude 身份」。

### 2.3 `skills/finish/SKILL.md` Step 7

`/finish` 委托 `/commit` 提交，补一句：commit skill 会**按当前执行 Agent 选 `Co-authored-by` 身份**（见 `/commit`），Codex 执行时不写 Claude 身份——避免在 finish 语境下又被默认成 Claude。

---

## 验证

无可执行测试。落地后做**文档自洽自查**：

1. `grep -n "停下\|等.*确认\|静默\|必停" skills/rebase/SKILL.md` —— 确认无「每阶段必停」残留、原则 #6 与各阶段措辞一致。
2. `grep -rn "Co-authored-by\|Codex\|Claude" GLOBAL_AGENTS.md skills/commit/SKILL.md skills/finish/SKILL.md` —— 确认三处署名规范一致、CC/Codex 两分支齐备。
3. 修改 `GLOBAL_AGENTS.md` / `skills/*` 后**无需重装**（软链即时生效）。

## 影响面 & 风险

- 纯文档；影响所有项目、CC + Codex 两端的 `/rebase`、`/commit`、`/finish` 行为叙述。
- #41 主风险：措辞漏改导致「原则说静默、阶段仍写必停」自相矛盾 → 由验证步骤 1 兜底。
- #44 主风险：身份判据若写得含糊，Agent 仍可能误选 → 用「你知道自己是哪个 Agent」+ 硬规则「Codex 绝不写 Claude」双保险。
