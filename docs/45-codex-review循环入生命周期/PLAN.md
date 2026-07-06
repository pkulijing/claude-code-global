# PLAN：把「review loop」做成开发过程中的自动收口环（round 45）

> 本轮 base 已 rebase 到最新 master（`ff5ee56` [round 44]）。经四轮澄清，方向已从「手动调用的 skill」彻底修正为「**自动触发的收口环**」。

## 背景与真正的目标

来源 teleop-operator round 12：CC 自审只发现 2 个并发隐患，codex（独立模型）review 补出 3 个 P1，其中「优雅停不可达」CC 完全漏判。硬实证——**同一个脑子自审自写的代码盲区一致**，尤其多线程/并发/复杂逻辑。

**根本诉求（澄清后）**：把「独立模型 review」从「偶尔想起来 / 人手动触发」变成**每个 commit 都必经的自动环**。具体拆成两件联动的事：

1. **commit 时机前移**：现状是我开发完**停下来干等**用户发话才 commit。改为——**我自己判断一个开发单元完成了，就主动收口 commit**，不再干等。
2. **commit 前内嵌 review loop**：主动 commit 之前，自动跑 review loop（独立模型 review → 自动修 → 复审 → 迭代到 clean）→ 才落 commit。**全程不停、不需用户介入**。

**用户角色前移到 `/finish`**：用户要 review 的不再是开发中间态，而是**一个每个 commit 都经过多轮 review loop、已经 clean 的完整分支**。开发过程中的 commit 由我全权把控。

## loop 是什么

**review → 修 → 再 review → 再修 → 直到无 P 级问题（clean）**。必须是 loop 而非单次，因为「修复本身可能引入新问题 / 首轮 review 未看全」，只有「修完复审到 codex 说没问题」才真正收敛。收敛判据明确：**复审报无 P 级问题 = clean = 退出**。

## 已确认的全部决策

| 维度          | 决策                                                                                                                             |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 触发时机      | 每次「我判断开发单元完成、准备 commit」时，自动触发；**不是 finish、不靠用户开口**                                               |
| 生效范围      | **写进宪法全局生效**（任何项目、任何 round、CC/Codex 两端）                                                                      |
| review 入口   | `/codex:review` 为主；复杂/设计存疑提示可加挂 `/codex:adversarial-review`                                                        |
| 降级          | codex 不可用（未装/token 失效/离线）→ **停下问用户**：重登录重试 / 降级本端自审（`/code-review`）+ 显著标注 / 跳过。绝不静默跳过 |
| 修复环节      | **我自动修 + 自动复审**，迭代到 clean，全程不停                                                                                  |
| commit 前确认 | 不停，直接 commit（用户事后在 finish 追溯）——否则退回「被动等发话」，与目标矛盾                                                  |
| 编排落点      | 抽成独立 `/review-loop` skill（有清晰输入输出契约），`/commit` 提交前自动调它                                                    |
| 琐碎改动      | 纯 docs/注释/单行 fix/配置微调 → 自动跳过 review（与 issue「琐碎可跳过」一致）                                                   |

## 关键设计

### 1. 只依赖稳定 slash command 入口

`/review-loop` 依赖 `/codex:review`、`/codex:setup`、`/code-review` 这些对外稳定命令；**绝不直接调 `codex-companion.mjs`**（codex plugin 内部脚本、路径带版本号 `.../1.0.4/...` 会随升级漂移）。

### 2. 双轨语义对称

「独立第二模型」两端不同：**CC 端为 codex、Codex 端为 CC**。skill 与宪法措辞都用对称表述，不写死单端。

### 3. review loop 是 /commit 的兄弟门禁

`/commit` 已有成熟的「提交前门禁」范式——第 4 步 **lint 检查**（探测项目类型→跑 lint→失败停下）。review loop 插在**同一位置**（lint 之后、生成 message 之前）作为兄弟步骤，风格对齐、心智一致。

## 开发内容

### A. 新增 `skills/review-loop/SKILL.md`（loop 编排的单一真源）

参照 `finish` 编排范式，文案贴 round 44 精简基调。frontmatter：`name: review-loop` / `disable-model-invocation: false` / description 点明「commit 前的自动 review 迭代环，独立模型优先、不可用降级本端自审并标注，迭代到 clean」。

body 步骤：

1. **定范围**：待提交的 diff（`git status --short` + `git diff`）。无变更 → 退出。
2. **琐碎跳过判定**：变更仅命中 `docs/` / 注释 / 单行 fix / 配置微调 → 打印「琐碎改动，跳过 review」并直接返回 clean（不烧 codex）。
3. **探测独立模型可用性**：走 `/codex:setup`，判 ready + 已登录。
4. **分支**：
   - 可用 → `/codex:review` 跑一轮，verbatim 呈现；复杂/设计存疑提示可加挂 `/codex:adversarial-review`。
   - 不可用 → **AskUserQuestion 停下三选项**：重登录重试 / 降级本端自审（`/code-review`）/ 跳过。降级 → 跑 `/code-review` + **显著标注**「⚠ 本次本端自审、盲区大、未经独立模型把关」。
5. **分诊 + 迭代收敛**：有 P0/P1 → **我自动修** → **自动回到步骤 4 复审** → 循环；无 P 级 → 返回「clean ✅」。
6. **留痕**：每轮结论追加到本轮 `docs/<N>-*/REVIEW.md`（第 N 轮发现什么、怎么修）——供 finish 时用户追溯。
7. 全篇「独立第二模型」用「CC 端 codex / Codex 端 CC」对称表述。

### B. 改 `/commit` skill：提交前自动内嵌 review loop

在现有第 4 步（lint）**之后**、生成 commit message **之前**插入一步：

> **提交前 review loop**：调 `/review-loop` 对本次待提交 diff 跑自动 review 迭代（独立模型优先、降级本端自审、琐碎跳过），**迭代到 clean 才继续生成 commit**。review loop 内部会自动修复并复审，不停下等用户。

### C. 改宪法 `GLOBAL_AGENTS.md`（主落点，全局生效）

两处联动：

1. **「核心开发模式」开头**（commit 时机前移）：增补一句——「开发过程中的 commit 由 Agent 自主把控：判断一个开发单元完成即主动收口，无需等用户发话；每次 commit 前自动经 review loop 迭代至 clean。用户的人工 review 前移到 `/finish`，面对的是每个 commit 都已过独立模型 review 的干净分支。」
2. **「需求生命周期·执行」条**末尾：增补一句——「执行阶段每次 commit 前自动走 **review 循环**（`/review-loop`：独立第二模型 review 优先——CC 端 codex、Codex 端 CC；不可用降级本端自审并标注——修复+复审迭代至无 P 级问题；琐碎改动可跳过）。」

（两端对称、点名 skill、贴精简基调。）

### D. 更新 `README.md`

- **Skills 表**：新增 `/review-loop` 一行，与其它 skill 平级并列（「并列项平等呈现」）。
- **`/commit` 行**：补一句「提交前自动内嵌 review loop（独立模型 review 迭代至 clean）」。
- **工作流串联**：反映「开发中 commit 自主把控 + commit 前自动 review」。

### E. 安装

新增 skill 目录后 `bash install.sh`（软链新 skill 到两端），在 `/finish` 收尾前于本 worktree 内执行。

## 不做

- 不做 hook（落点 C 原案）：判定「并发/复杂」难准、易噪音；改动特征判定放进 `/review-loop` 的「琐碎跳过」逻辑里，够用。
- 不重造 codex 调用：完全复用 `/codex:review` / `/codex:setup`。
- 不用 codex 的 `--enable-review-gate`（每次 stop 都触发，粒度太粗、过频）——我们要的是「commit 前」而非「每次 stop」。

## 涉及文件

- 新增：`skills/review-loop/SKILL.md`
- 改：`skills/commit/SKILL.md`（lint 后插入 review loop 步骤）
- 改：`GLOBAL_AGENTS.md`（核心开发模式 + 执行条，两处）
- 改：`README.md`（Skills 表 + /commit 行 + 工作流）
- 运行：`bash install.sh`
- 本轮产物：`docs/45-codex-review循环入生命周期/`（PROMPT + PLAN + 自举产生的 REVIEW.md）

## 验证

1. **install 生效**：`ls -l ~/.claude/skills/review-loop/SKILL.md ~/.codex/skills/review-loop/SKILL.md` 均为软链。
2. **skill 可解析**：`/review-loop` 进可用 skill 列表、description 正确。
3. **端到端自举**（核心验证）：本轮结束前，用新 `/commit` 提交本轮改动——观察它在生成 message 前**自动**调 `/review-loop`：
   - codex 可用路径：触发 `/codex:review` → 若报 P 级则我自动修 → 自动复审 → clean → 才 commit，全程不停问我。
   - 降级路径：走查 `/codex:setup` 不可用分支的停下三选项 + 降级自审显著标注。
   - 琐碎跳过：纯 docs 改动确认自动跳过、不烧 codex。
4. **一致性**：`grep -n review-loop GLOBAL_AGENTS.md README.md skills/commit/SKILL.md` 四处落点齐、措辞两端对称。
