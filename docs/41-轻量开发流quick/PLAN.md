# PLAN：轻量开发流 `/quick`

## 一、设计定位：三档开发流

落地后形成「按需求重量选流程」的三档谱系，`/quick` 补最轻一档：

| 档位           | 入口                               | worktree | 分支                        | docs 三件套         | 计划模式 | 收尾仪式                                   | 适用                             |
| -------------- | ---------------------------------- | -------- | --------------------------- | ------------------- | -------- | ------------------------------------------ | -------------------------------- |
| 重（默认）     | `/start` → `/finish`               | ✓        | `round<N>-*`                | PROMPT/PLAN/SUMMARY | ✓        | devtree/沉淀/README/关 issue/worktree 收尾 | 复杂开发、需追踪                 |
| 中             | `/start --no-worktree` → `/finish` | ✗        | 当前分支                    | PROMPT/PLAN/SUMMARY | ✓        | 同上（跳 worktree 收尾）                   | 不值单开 worktree 但仍需文档追踪 |
| **轻（新增）** | **`/quick`**                       | ✗        | 当前分支（可选 `--branch`） | **无**              | **无**   | **仅 `/commit`**                           | **小函数改一下、说清楚即可**     |

`/quick` 的心智模型是「直接干 → commit 说清楚就完」，本质是一个 skill 从头管到尾，不像 start/finish 因中间要 review PLAN 而拆成两截。

## 二、`skills/quick/SKILL.md` 结构

frontmatter 与既有 skill 一致（`name: quick` / `description` / `disable-model-invocation: false`）。正文按以下步骤：

### 参数解析

args 可含（三者正交、可组合）：

- `--branch`：切轻量分支 `quick/<描述>`（不建 worktree），改完 commit 留在该分支等用户手动合。默认不带 = 当前分支直接改。
- `#<issue 号>` 或 issue URL：让收尾 commit 带 `Closes #N`（复用 `platform_issue.py` 语义，但**仅取号**、不拉 issue 详情——简易流不需要把 issue body 落成文档）。可传多个。
- 剩余文字 = 本次小改动的需求描述。

无描述且无法从对话上下文推断要改什么 → 追问用户改什么。

### 前置心智（写进 SKILL，供未来的 AI 自我校准）

`/quick` 是**明确的轻量流**，命中以下信号应该反问用户「是否该走正规 `/start`」而非硬用 quick：需求需要计划模式讨论方案、需要落 PROMPT/PLAN 追踪、涉及多文件架构改动、需要 devtree 记一个 Epic 节点。quick 只服务「一眼能说清、改动局部、无需追踪」的小改。

### Step 1：（可选）切轻量分支

仅当 `--branch`：

- 探测主分支（`git symbolic-ref --short refs/remotes/origin/HEAD` 取末段，失败本地探 `main`/`master`）。
- `git switch -c quick/<描述>`（从当前 HEAD 切，不建 worktree）。
- 若工作区已有未提交改动 → 提示用户（切分支会带走改动），让用户确认。
  默认（不带 `--branch`）：跳过，确认当前所在分支即为想改的分支（当前分支就是主分支也允许——简易流小改直提主分支是合理的，但打印一行提示让用户知情）。

### Step 2：直接实现

按需求描述直接改代码。遵循项目既有规则（命中语言/栈触发条件时先 Read 对应 `rules/*.md`——与所有开发一样，简易流不豁免规则）。**不写 PROMPT/PLAN/SUMMARY，不建 docs 目录，不进计划模式。** 把「为什么这么改」的关键信息记住，供 Step 3 的 commit message 用（呼应 `rules/python.md` §3.4「注释写当前真相、不写演化历史」——commit message 承载「为什么」）。

### Step 3：收尾——调用 `/commit`

调用 `/commit` 提交（继承其 lint 门禁 / semantic message / Co-authored-by trailer，单一真源不重复实现）：

- 若 Step 解析出 `#N`：把 `Closes #N`（多个则每个各一行、各带关键字——重申 `/finish` Step 4 的硬规则，防「一行只关第一个」）作为额外上下文传给 `/commit`，让 message body 自然包含。
- `[round N]` 前缀：`/quick` 默认不建 round 分支、不建 docs 目录 → `/commit` 的两路探测都判不出 N → 走普通 commit 不加前缀。**这是预期行为**（简易流不进轮次追踪），SKILL 里点明即可，无需特殊代码。

### Step 4：轻量收尾提示

打印一行：

- 若 `--branch`：提示分支名 + 「改动在 `quick/<描述>` 分支，review 后自行 merge / 提 PR」。
- 默认：提示已提交到当前分支，是否 `push` 由用户决定（与既有不自动 push 约定一致）。
- 统一附一句：「如果这个改动其实需要文档追踪 / 计划讨论，下次走 `/start`。」

**明确不做**（SKILL 里显式列，划清与 `/finish` 边界）：不写 SUMMARY、不跨项目沉淀反思、不调 `/devtree`、不 review README、不做 issue 生命周期管理（`/finish` 那套关联并关闭 issue）、不做 worktree 收尾。

## 三、README.md 改动

1. skills 表（第 89 行附近）新增一行：
   `| `/quick`| 轻量开发流：不落 docs / 不开 worktree / 不进计划模式，直接改 → 自动`/commit`收尾（可选`--branch` 切轻量分支、`#<issue>` 带 Closes）。适合「小函数改一下、说清楚即可」的小改 |`
2. skills 表引导语（第 87 行）或紧邻处点一句三档选择：重流程 `/start`+`/finish`、轻量流 `/quick`。
3. 只动相关段落，不重写整篇（遵循 `/finish` Step 6 的 README review 约定）。

## 四、GLOBAL_AGENTS.md 改动

改写第 37 行现有那句，把 `/quick` 引入为更轻一档（与 `--no-worktree` 并列，不删原提法）：

> 现：`……；轻量改动可用 `/start --no-worktree` 在当前分支直接干。`
> 改为：`……；不值得单开 worktree 的轻量改动可用 `/start --no-worktree`在当前分支直接干；连 docs 三件套都不需要的小改（如改个小函数、说清楚即可）用`/quick` 直接改 → 自动 commit 收尾。`

放在「核心开发模式」段，是全局规范里对三档流程的唯一权威指针。

## 五、install.sh

无需改代码——install.sh 已 `for skill_dir in skills/*/` 逐目录软链（见 install.sh:303）。新增 `skills/quick/` 后**重跑 `bash install.sh`** 即软链到两端 `~/.claude/skills/quick` 与 `~/.codex/skills/quick`。这一步由 `/finish` 之外手动执行（项目 CLAUDE.md 明确「新增 skill 目录后需重跑 install.sh」）。

## 六、测试策略

本轮产物是 skill 的 Markdown 指令文档 + README/规范文本改动，**无可单测的业务逻辑代码**（无纯函数 / 算法 / 有 IO 契约的模块），故不涉及 TDD 单测。验证方式为人工核对：

1. `bash install.sh` 成功、`~/.claude/skills/quick/SKILL.md` 软链存在且指向仓库。
2. SKILL.md 步骤自洽：参数解析、`--branch` / `#issue` / 描述三者组合无歧义。
3. README / GLOBAL_AGENTS 改动只动相关段、无破坏既有表格结构。

## 七、执行顺序

1. 写 `skills/quick/SKILL.md`
2. 改 `README.md`（skills 表 + 引导语）
3. 改 `GLOBAL_AGENTS.md`（第 37 行三档指针）
4. `bash install.sh` 验证软链
5. 走 `/finish` 收尾本轮（本轮是新增面向用户 skill，触发 README review——已在 Step 2 前置，devtree 记节点，commit）
