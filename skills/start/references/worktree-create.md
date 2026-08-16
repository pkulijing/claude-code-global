# worktree 创建细则（`/start` 通用流程第 4 步展开）

> `/start` 通用流程第 4 步读本文。**args 含 `--no-worktree` 时整节跳过**，在当前分支直接开发、docs 目录落在当前工作树；`/finish` 收尾时检测到非 worktree 会跳过 worktree 收尾，对称无悬空分支。

默认每轮开发在独立 git worktree 内进行，让多轮可并行、互不污染主工作树：

- **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（得 `origin/master` → 取末段 `master`）；失败则本地探测 `main` / `master`。（「远端对齐」小节的 `<主分支>` 与这里是同一次探测，探一次两处复用。）
- **防嵌套**：若当前已在某个 linked worktree 内（`git rev-parse --git-dir` ≠ `git rev-parse --git-common-dir`）→ 停下提示用户「已在 worktree 内」，问是接续当前轮还是退出，**不嵌套创建 worktree**。
- **确保 worktree 目录被忽略（优先复用全局）**：先 `git check-ignore -q .claude/worktrees` 探测是否已被忽略 —— 这会自动吃到全局 `core.excludesFile`（很多人已在 `~/.gitignore_global` 里全局忽略 `.claude/worktrees`）与任何本地规则。**已忽略 → 什么都不做**，绝不冗余落 `.claude/.gitignore`。仅当**未忽略**时，才创建 / 追加 `.claude/.gitignore` 忽略 `worktrees/`（幂等），避免主工作树把嵌套 worktree 当 untracked。
- **建之前先确认这个 N 没被别人占走**（第 2 步的信号可能已滞后）：

  ```bash
  git branch    --list "round<N>" --list "round<N>-*"                # 本地
  git branch -r --list "origin/round<N>" --list "origin/round<N>-*"  # 远端，吃第 1 步那次 fetch
  ```

  **两条都要跑，别图省事合成一条 `git branch -a`** —— `-a` 配不带 `origin/` 前缀的 pattern **匹配不到远端分支**（实测：`git branch -a --list "round59-*"` 对着 `remotes/origin/round59-bar` 返回空），只查本地恰好漏掉「别的设备已经推上去了」这个主要场景。

  任一条有输出 → **重算 N 取下一个空位，别靠换个描述词绕开**。这步不能省：描述不同的 `round<N>-a` / `round<N>-b` 会各自建成功、git 不会拦，撞号一路潜伏到合并时才炸。

- **创建**：worktree 目录名与分支名统一为 `round<N>-<英文短描述>`，**整串纯 ASCII**：

  ```bash
  git worktree add .claude/worktrees/round<N>-<英文短描述> -b round<N>-<英文短描述> <主分支>
  ```

  **短描述规格（照做，别自由发挥）**：字符集 `[a-z0-9-]`（小写字母 / 数字 / 连字符）；**短描述本身 ≤ 20 字符**（不含 `round<N>-` 前缀）、2–4 个词；与第 3 步的中文描述同义即可（`开轮远端对齐` → `remote-align`、`review 成本与思考深度调优` → `review-cost-tuning`）。没有自然英文对应的专名用拼音。**实在起不出好名字就退回裸 `round<N>`** —— 那是合法命名，别为了凑名字硬造缩写。

  **为什么必须 ASCII**：GitHub 网页端**导航不进非 ASCII 分支名的文件树**。缺陷在其前端而非服务端 —— 同一个 percent-encoded URL 直接 `curl` 返回 200 且页面内容完整，属上游问题、我们只能规避。约束只落在 **ref 位置**（分支名、以及与之同名的 worktree 目录）；`docs/<N>-<中文描述>/` 这类 **path 位置**的中文照旧保留，形如 `/tree/<sha>/docs/1-第1章-信息论导引` 实测可正常打开。

- **进入**：`cd` 进新 worktree 目录，其后所有文件操作、git 操作都在该 worktree 内进行。
- **告知**：打印一行 worktree 路径与分支名，提示用户可在 IDE 中打开该目录并行开发。

**新 worktree 里 gitignored 的运行时依赖一概不存在**——`git worktree add` 只 checkout **tracked 文件**，于是 `node_modules/`、`.env.local` / 本地凭证、build 产物、本地缓存等在新 worktree 里全部缺失。凡在 worktree 内跑门禁 / 起服务 / 跑真机脚本都会撞上，且**与栈无关**（实测两例：前端门禁缺 `node_modules`，`tsc` / `biome` / `vite build` 因找不到 devDependency 直接炸；一次性核对脚本缺 `.env.local`，读不到云厂商 AK/SK）。两种通用应对，按依赖性质二选一：

1. **软链主 checkout**（重依赖、目录级，如 `node_modules/`）：`ln -s <主checkout>/<path> <worktree>/<path>`，**跑完即删、切勿 commit**——`node_modules/` 这类带尾斜杠的 gitignore 模式只匹配目录、**不匹配软链**，软链会以 untracked 身份冒进 `git status`。（也可选择在 worktree 内重新准备一份，如 `npm install`，代价是磁盘与时间。）
2. **回退主 checkout 路径**（只读小文件，如 `.env.local` / 凭证）：在脚本 / 工具里显式「优先 worktree 根的该文件、缺则回退主 checkout 同名文件」，比软链更轻、无残留风险。

前端场景的具体解法见 `playbooks/frontend.md` §1。
