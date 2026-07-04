---
name: quick
description: 轻量开发流：不落 docs / 不开 worktree / 不进计划模式，直接改代码后自动 /commit 收尾。适合「小函数改一下、说清楚即可」的小改；要文档追踪或计划讨论请走 /start
disable-model-invocation: false
---

用户调用此 skill 表示要走**轻量开发流**：一个很小的需求（如改一个小函数、修个笔误、调一处配置），不值得引入 `/start` + `/finish` 的重量级文档三件套，只要在 commit message 里把「改了啥、为什么」说清楚即可。

`/quick` 是「三档开发流」里最轻的一档：

| 档         | 入口                               | worktree | docs 三件套         | 计划模式 | 收尾仪式                                               |
| ---------- | ---------------------------------- | -------- | ------------------- | -------- | ------------------------------------------------------ |
| 重（默认） | `/start` → `/finish`               | ✓        | PROMPT/PLAN/SUMMARY | ✓        | devtree / 沉淀反思 / README / 关 issue / worktree 收尾 |
| 中         | `/start --no-worktree` → `/finish` | ✗        | PROMPT/PLAN/SUMMARY | ✓        | 同上（跳 worktree 收尾）                               |
| **轻**     | **`/quick`**                       | ✗        | 无                  | 无       | 仅 `/commit`                                           |

`/quick` 从头管到尾（直接干 → commit 说清楚就完），不像 start/finish 因中间要人 review PLAN 而拆成两截。

## 前置判断：这个需求真的适合 `/quick` 吗

`/quick` 只服务「一眼能说清、改动局部、无需追踪」的小改。命中以下任一信号，**先停下反问用户「是否该走正规 `/start`」**，而不是硬用 quick：

- 需求需要进计划模式讨论方案、或方案本身有分歧要先对齐；
- 需要落 PROMPT/PLAN 供未来追踪，或值得在开发树（`docs/DEVTREE.md`）记一个 Epic 节点；
- 涉及多文件的架构改动、跨模块重构；
- 对应一个需要长期追踪的 issue（长期可追踪的开发项推荐 `/backlog` + `/start <issue#>`）。

用户坚持用 quick 或确属小改 → 继续。

## 参数解析

args 可含以下项（三者正交、可任意组合），解析后剩余文字即本次小改动的需求描述：

- **`--branch`**：切一个轻量分支 `quick/<描述>`（**不建 worktree**），改完 commit 留在该分支等用户手动合 / 提 PR。默认不带 = 在当前分支直接改。
- **`#<issue 号>` 或 issue URL**：让收尾 commit 带 `Closes #N`。**只取号、不拉 issue 详情**（简易流不需要把 issue body 落成文档）；可传多个。
- **剩余文字**：需求描述。

无描述且无法从对话上下文推断要改什么 → 追问用户改什么，拿到后再继续。

## Step 1：（可选）切轻量分支

**仅当 args 含 `--branch`**：

- 探测主分支：`git symbolic-ref --short refs/remotes/origin/HEAD`（得 `origin/master` → 取末段）；失败则本地探测 `main` / `master`。
- 若工作区已有未提交改动 → 提示用户「切分支会带走当前未提交改动」，等用户确认。
- `git switch -c quick/<描述>`（从当前 HEAD 切，`<描述>` 从需求描述提炼，**不建 worktree**）。

**默认（不带 `--branch`）**：跳过本步，在当前所在分支直接改。若当前分支就是主分支（`master` / `main`），**允许**——简易流小改直提主分支是合理的，但打印一行提示让用户知情（「将在主分支 `<主分支>` 上直接改并提交」），给用户一个喊停的机会。

## Step 2：直接实现

按需求描述直接改代码。**不写 PROMPT/PLAN/SUMMARY、不建 docs 目录、不进计划模式。**

- **规则不豁免**：命中语言 / 栈触发条件时照常先 Read 对应 `rules/*.md`（Python / 前端 / ROS 2 / shell / lark）—— 简易流省的是「文档仪式」，不是「代码规范」。
- 把「为什么这么改」的关键信息记住，供 Step 3 的 commit message 用（commit message 承载「为什么」，代码本身说清「做了什么」）。
- 若确有必要，可加一行行内注释解释非显然的设计动机（写「当前真相」，不写「本轮 / issue #N」这类演化历史标记）。

## Step 3：收尾 —— 调用 `/commit`

调用 `/commit` 提交（继承其 lint 门禁 / semantic commit message / Co-authored-by trailer，单一真源不重复实现）：

- **若解析出 `#N`**：把 `Closes #N` 作为额外上下文传给 `/commit`，让 message body 自然包含（不嵌入 title）。**关多个 issue 时每个 `#N` 各占一行、各带 `Closes` 关键字**（`Closes #13` / `Closes #20` / …）—— 绝不写成 `Closes #13 #20`（GitHub / GitLab 的关闭关键字只对紧跟的第一个号生效，后面的不会关，这是 `/finish` 里踩过的坑）。
- **`[round N]` 前缀天然不加**：`/quick` 默认既不建 `round<N>-` 分支、也不建 `docs/<N>-*/` 目录 → `/commit` 的两路轮次探测都判不出 N → 走普通 commit、不加前缀。**这是预期行为**（简易流本就不进轮次追踪），无需干预。

## Step 4：轻量收尾提示

打印一行收尾提示，按分支策略分岔：

- **`--branch`**：「改动已提交到 `quick/<描述>` 分支，review 后自行 merge / 提 PR。」
- **默认**：「已提交到当前分支 `<分支名>`，是否 `git push` 由你决定。」（与全局不自动 push 的约定一致。）

统一附一句：「如果这个改动其实需要文档追踪 / 计划讨论 / 开发树记节点，下次走 `/start`。」

## 明确不做（与 `/finish` 的边界）

`/quick` **一概不碰**以下重流程独有的仪式 —— 要这些就走正规 `/start` + `/finish`：

- 不写 SUMMARY.md
- 不做跨项目可沉淀流程反思、不向 claude-code-global 提 issue
- 不调 `/devtree`
- 不做 README review & update
- 不主动做 issue 生命周期管理（`/finish` 那套「关联并关闭 issue」——「刻意不做」归档为 `wontfix` closed issue 等）；`/quick` 只在你显式传 `#<issue>` 时顺手在 commit 带 `Closes #N`，不替你去改 issue 状态
- 不做 worktree 收尾（rebase / FF merge / 清理 worktree·分支·tag）
