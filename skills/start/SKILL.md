---
name: start
description: 开始一个新的开发项：创建文档目录，撰写 PROMPT.md 和 PLAN.md，确认后再开始写代码
disable-model-invocation: false
---

用户调用此 skill 表示要开始一个新的开发项。

**前置检查**：若 `CLAUDE.md` 与 `DEVTREE.md` 都不存在，停下来提示用户先运行 `/bootstrap`，**不要**自己兜底建项目骨架。`/start` 只负责开新一轮开发，不负责项目首次初始化。

**参数处理**：调用时可能附带参数（args），参数有两种形态：

- **issue 驱动**（推荐）：参数是 `#<数字>` 或完整 issue URL：
  - GitHub: `https://github.com/owner/repo/issues/N`
  - GitLab: `https://gitlab.com/<namespace>/<project>/-/issues/N`（自托管把 host 换为对应实例域名）
  - 走「issue 驱动分支」（见下文）
- **自由描述**：参数是对需求的自由文字描述
  - 走「自由描述分支」（与原流程一致）

无参数 → 追问用户本次开发项的需求是什么或对应的 issue 号，拿到后再继续。

**`--no-worktree` 开关**：args 中可附带 `--no-worktree`（与 issue# ／自由描述正交，可与二者同时出现）。默认每轮在独立 git worktree 内开发；带此开关则跳过 worktree 创建、在当前分支直接干。解析需求内容前先把 `--no-worktree` 从 args 中剔除。适用场景：轻量改动 / 探索性 round / 不值得单开 worktree 的小修复。

按照全局 CLAUDE.md 中的开发模式，严格遵循「执行前必须先完成 PROMPT.md 和 PLAN.md 的撰写并确认，再开始写代码」：

### 通用流程

1. **确定轮次编号 N**：扫 `docs/` 下现有 `N-*` 目录取最大值 +1。
2. **确定本轮中文描述**：issue 驱动 → 先按「issue 驱动分支」第 1 步调 helper 拉 issue 详情，从 issue 标题提炼简短中文描述；自由描述 → 从描述文字提炼。
3. **创建 worktree**（默认；带 `--no-worktree` 时跳过本步）—— 见下方「worktree 创建」小节。
4. 在 `docs/` 下创建开发项文件夹 `docs/<N>-<中文描述>/`（worktree 模式下落在新 worktree 内）。
5. 基于参数撰写 `PROMPT.md`（两个分支具体行为见下）。
6. 进入计划模式，撰写 `PLAN.md` 并请用户确认。
7. 用户确认后再开始写代码。

#### worktree 创建（通用流程第 3 步展开）

默认每轮开发在独立 git worktree 内进行，让多轮可并行、互不污染主工作树。除非 args 含 `--no-worktree`，执行：

- **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（得 `origin/master` → 取末段 `master`）；失败则本地探测 `main` / `master`。
- **防嵌套**：若当前已在某个 linked worktree 内（`git rev-parse --git-dir` ≠ `git rev-parse --git-common-dir`）→ 停下提示用户「已在 worktree 内」，问是接续当前轮还是退出，**不嵌套创建 worktree**。
- **确保 worktree 目录被忽略（优先复用全局）**：先 `git check-ignore -q .claude/worktrees` 探测是否已被忽略 —— 这会自动吃到全局 `core.excludesFile`（很多人已在 `~/.gitignore_global` 里全局忽略 `.claude/worktrees`）与任何本地规则。**已忽略 → 什么都不做**，绝不冗余落 `.claude/.gitignore`。仅当**未忽略**时，才创建 / 追加 `.claude/.gitignore` 忽略 `worktrees/`（幂等），避免主工作树把嵌套 worktree 当 untracked。
- **创建**：worktree 目录名与分支名统一为 `round<N>-<中文描述>`（`<中文描述>` 同第 4 步 docs 目录的描述）：

  ```bash
  git worktree add .claude/worktrees/round<N>-<中文描述> -b round<N>-<中文描述> <主分支>
  ```

- **进入**：`cd` 进新 worktree 目录，其后所有文件操作、git 操作都在该 worktree 内进行。
- **告知**：打印一行 worktree 路径与分支名，提示用户可在 IDE 中打开该目录并行开发。

带 `--no-worktree` → 跳过本小节，在当前分支直接开发，docs 目录落在当前工作树。`/finish` 收尾时检测到非 worktree 会跳过 worktree 收尾，对称无悬空分支。

### issue 驱动分支

参数命中 `#数字` 或上述任一平台的 issue URL 时：

1. **拉 issue 详情**：调 helper（自动按 `git remote get-url origin` 走 GitHub 或 GitLab）：

   ```bash
   python3 $HOME/.claude/scripts/platform_issue.py issue-view <N>
   ```

   如参数是完整 URL，先从中提取 N。helper stdout 输出归一 json（GitHub 风格字段），schema 固定为：

   ```json
   {
     "number": 3,
     "title": "...",
     "body": "...",
     "url": "https://...",
     "labels": ["type:X", "area:Y", "priority:Z"]
   }
   ```

   GitLab 端的 `iid` / `web_url` / `description` 已在 helper 内归一为 `number` / `url` / `body`，本 SKILL 直接按上述 schema 读字段。

2. **PROMPT.md 顶部**写一段引用块（让未来的人或 AI 一眼看到来源）：

   ```markdown
   > 来自 [#<N> <issue 标题>](<issue URL>)
   > Labels: `type:X` `area:Y` `priority:Z`
   ```

3. **PROMPT.md 主体**：把 issue body 内容作为「背景 / 需求」段的起点，AI 据此扩写完整的 PROMPT.md（可能基于 issue body 增补：约束、范围、待决问题等）。如 issue body 已足够完整，直接复用为主要内容。
4. 文件夹命名：从 issue 标题提炼简短中文描述，规则：`docs/<编号>-<中文描述>/`

### 自由描述分支

参数是文字描述时（非 issue 引用）：流程同原版。AI 基于参数撰写 PROMPT.md，文件夹命名从描述提炼。

> 提示：自由描述分支适合「轻量改动 / 探索性 round / 不需要长期追踪的开发项」。**长期可追踪的开发项推荐先 `/backlog` 创 issue，再 `/start <issue#>`**。
