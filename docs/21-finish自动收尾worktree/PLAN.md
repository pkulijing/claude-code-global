# PLAN — Round 21：worktree 化的可并行开发工作流

## 1. 目标与范围

issue #9 原本只要求 `/finish` 自动收尾 worktree。计划阶段用户扩展了范围：**把整个开发工作流改造成基于 worktree 的可并行流程**。本轮因此覆盖两端对称改造：

- **`/start`**：每轮开发默认创建独立 git worktree + 分支（开「口」）
- **`/finish`**：在 worktree 内收尾时自动「rebase → FF merge → 清理」（收「口」）

两者对称：`/start` 开 worktree，`/finish` 关 worktree，中间多轮可并行互不污染。

## 2. 决策记录（计划阶段已和用户确认）

| 决策点            | 结论                                                                                                                                                                                                       |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Step 5 实现方式   | **方向 A 内联**：`/finish` Step 5 自描述完整 worktree 收尾流程，遵循 `/rebase` 核心原则，但**不硬调用** `/rebase` skill（因 `/rebase` 阶段 3 的 `git checkout master` 在 worktree 下会失败，无法干净复用） |
| worktree 目录位置 | 仓库内 `.claude/worktrees/round<N>-<desc>/`（CC 默认 worktree 位置）；需 gitignore                                                                                                                         |
| 默认开 + 逃生舱   | `/start` 默认建 worktree；`args` 含 `--no-worktree` 时跳过，在当前分支直接干                                                                                                                               |
| GLOBAL_CLAUDE.md  | 加一句简述：每轮在独立 worktree 进行，支持并行                                                                                                                                                             |

**命名约定**：worktree 目录名与分支名统一为 `round` + docs 目录名，即 `round<N>-<docs目录中文描述>`。例：docs 目录 `21-finish自动收尾worktree` → 分支/worktree 名 `round21-finish自动收尾worktree`。git 原生支持 UTF-8 分支名。

## 3. Part A — `/start` 默认创建 worktree

改 `skills/start/SKILL.md` 的「通用流程」段。新流程：

1. **前置检查**（不变）：`CLAUDE.md` 与 `DEVTREE.md` 都不存在 → 提示先 `/bootstrap`。
2. **确定轮次编号 N**：扫 `docs/` 现有 `N-*` 目录，取最大值 +1。
3. **决定是否建 worktree**：
   - `args` 含 `--no-worktree` → 跳过 worktree，在当前分支直接干（流程同旧版），并把该 flag 从 args 里剔除后再解析 issue#/自由描述。
   - 否则进入建 worktree 子步。
4. **建 worktree 子步**：
   - 探测主分支：`git symbolic-ref --short refs/remotes/origin/HEAD`（得 `origin/master` → 取 `master`）；失败则本地探测 `main` / `master`。
   - 若当前已在某 linked worktree 内（`git rev-parse --git-dir` ≠ `--git-common-dir`）→ 停下提示用户「已在 worktree 内」，问是接续当前轮还是退出，**不嵌套建 worktree**。
   - 确保 `.claude/.gitignore` 忽略 `worktrees/`：不存在或未含则创建/追加（幂等）。
   - `git worktree add .claude/worktrees/round<N>-<desc> -b round<N>-<desc> <主分支>`。
   - `cd` 进新 worktree 目录；其后所有文件操作都在该 worktree 内进行。
   - 打印一行告知用户：worktree 路径 + 分支名，提示可在 IDE 中打开该目录。
5. **创建 `docs/<N>-<desc>/` 文件夹**（在 worktree 内）。
6. 撰写 `PROMPT.md`（issue 驱动 / 自由描述两分支逻辑不变）。
7. 进入计划模式撰写 `PLAN.md`，请用户确认。
8. 确认后写代码。

参数说明段补充 `--no-worktree` 的含义与适用场景（轻量改动 / 探索性 round）。

## 4. Part B — `/finish` 新增 Step 5「worktree 收尾」

改 `skills/finish/SKILL.md`：在 Step 4（`/commit`）之后插入 **Step 5：worktree 收尾**，原 Step 5（轻量提示）顺延为 **Step 6**。

### Step 5 逻辑

1. **检测是否在 worktree 内**：`git rev-parse --git-dir` 与 `--git-common-dir` 不一致 → 在 linked worktree 内。
   - **不在 worktree** → 打印一行「non-worktree round，跳过 worktree 收尾」，直接进 Step 6。
   - **在 worktree** → 进入收尾流程。
2. **诊断**：展示 `git worktree list`、当前分支、`git status`（应干净，`/commit` 刚跑完）、`git log --graph --oneline -15`。
3. **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD` → `master`/`main`；无 origin 则本地探测。
4. **前置检查**：当前分支不能就是主分支；工作区必须干净。异常 → 停下问用户。
5. **备份 tag**：`git tag backup/<branch>-$(date +%Y%m%d-%H%M)`，告知用户回退命令。
6. **rebase 到主分支**：`git rebase <主分支>`。
   - **无冲突** → 展示 graph，停下等用户确认。
   - **有冲突**（issue 实测 DEVTREE.md 几乎必冲突）→ `git status` 列冲突文件，**逐个解 + `git add`**，`git rebase --continue`；后续 commit 续冲突则重复。`git rebase --abort` + 备份 tag 作兜底。**冲突时暂停让用户解，不自动跳过。**
7. **worktree-aware FF merge**：主分支 checkout 在**主 worktree**，不能在当前 worktree `git checkout`。
   - 算主 worktree 路径：`dirname` of `git rev-parse --path-format=absolute --git-common-dir`。
   - `git -C <主worktree> merge --ff-only <当前分支>`。
   - 若 FF 失败（主分支期间又前进）→ 回到第 6 步把当前分支继续 rebase 到最新主分支，重试。**禁止 fallback 普通 merge。**
8. **二次确认 + 销毁性清理**：明确列出将删除的「worktree 目录 + 分支 + backup tag」，等用户确认。
   - 用户**确认** → 先 `cd <主worktree>`（当前 cwd 即将失效），再依次：
     - `git worktree remove <当前worktree路径>`
     - `git branch -d <当前分支>`
     - `git tag -d backup/<branch>-...`
   - `git worktree remove` 失败（IDE 占用文件）→ 给清晰提示「关闭打开该目录的编辑器后重试」，**不硬删**，保留状态。
   - 用户**拒绝** → 保留全部状态（worktree / 分支 / tag 都留），打印当前状态，结束。
9. **不自动 push**：打印一行提示，推送由用户决定（与 finish 现有约定一致）。

### cwd 处理要点（写进 skill 文档）

Step 5 跑在 feature worktree 内（CC 的 Bash cwd）。rebase 必须在此 cwd 跑；FF merge 用 `git -C <主worktree>` 跑；清理前必须先 `cd <主worktree>`，否则 `git worktree remove` 删掉自己脚下的目录导致后续 Bash 失效。

## 5. Part C — 配套改动

- **`.claude/.gitignore`**（新建）：忽略 `worktrees/`，避免主 worktree `git status` 把嵌套 worktree 当 untracked。遵循全局「.gitignore 按目录拆分」规则。
- **`GLOBAL_CLAUDE.md`**：在「核心开发模式」段加一句简述——每轮开发默认在独立 git worktree 内进行（`/start` 自动建、`/finish` 自动收尾），支持多轮并行。
- **`README.md`**：`/finish` Step 3.5 会判定本轮命中「面向用户的工作流改动」触发清单 → 在 finish 阶段更新 README 中 `/start`、`/finish` 的描述。

## 6. 验证策略

本轮产物是 skill 指令文档（markdown），非有输入→输出契约的业务逻辑，无适用的自动化单测；仓库也无 skill 测试框架。验证方式：

- **dry-run 推演**：对照「在 worktree / 不在 worktree」「rebase 有冲突 / 无冲突」「清理确认 / 拒绝」「`worktree remove` 失败」各分支逐条走查 skill 文档，确认每条路径有明确指令。
- **关键命令实测**：在临时 worktree 里实测 `git rev-parse --git-dir`/`--git-common-dir` 差异、`git -C <主worktree> merge --ff-only`、`git worktree remove` 的行为，确认命令正确。
- **活体集成测试**：下一轮（Round 22）即首个走新 `/start` 的 worktree round，`/finish` 时实测 Step 5 全流程。

## 7. Round 21 自身不走 worktree

本次 `/start 9` 已在 master 主 worktree 上启动（docs/21 目录、PROMPT.md 已落在 master）。且 `~/.claude/skills/*` 是指向**主 worktree** 仓库文件的软链——在 worktree 分支里改 skill 不会立即生效，要等合回 master。故 Round 21 自身留在 master 主 worktree 完成，新工作流从 Round 22 起生效。这是「创建工作流的那一轮无法用该工作流自举」的务实取舍。

## 8. 风险与不做的事

- **不改 `/rebase`**：保持 scope 收敛，`/rebase` 阶段 3 仍是非 worktree 场景的 checkout+merge；worktree 场景由 `/finish` Step 5 自己处理。
- **不引入新工具/脚本**：纯 skill 文档改动 + 一个 `.claude/.gitignore`。
- **嵌套 worktree 的 untracked 噪音**：靠 `.claude/.gitignore` 的 `worktrees/` 消除；对没有该 gitignore 的老项目，`/start` 会幂等补写。
- **Chinese 分支名**：git 原生支持 UTF-8，macOS/Linux 文件系统支持；若未来某项目环境有问题再议。
- **`--no-worktree` round 的收尾**：在当前分支直接干、不建分支，`/finish` 检测到非 worktree 即跳过 Step 5，`/commit` 在当前分支提交即可，对称且无悬空分支。
