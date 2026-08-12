---
name: start
description: 开始一个新的开发项：创建文档目录，撰写 PROMPT.md 和 PLAN.md，确认后再开始写代码
disable-model-invocation: false
---

用户调用此 skill 表示要开始一个新的开发项。

**前置检查**：若 `CLAUDE.md` 与 `docs/DEVTREE.md` 都不存在，停下来提示用户先运行 `/bootstrap`，**不要**自己兜底建项目骨架。`/start` 只负责开新一轮开发，不负责项目首次初始化。

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

1. **远端对齐**（`git fetch` + 撞车检查）—— 见下方「远端对齐」小节。**必须排在最前**：轮次编号要用远端信号；而撞车检查得赶在建 worktree / 建 docs 之前，否则拦下来时已经落了一个分支和一个目录要清。
2. **确定轮次编号 N**：取「已占用编号」并集的最大值 +1。**为什么要并集**：并行多 round 各在独立 worktree、未合回主分支时，新建的 `docs/<N>-*` 尚未合入、本树看不见，只扫本树 `docs/` 会让各 round 算出同一个 N+1，合入时撞车；而多设备 / 云端 routine 并行时，**本地信号还会整体滞后于远端**。故五个信号源取并集：
   1. **本树 `docs/`**：现有 `docs/<N>-*` 目录名解析出的 N；
   2. **在途分支名**：`git branch --list 'round*'` 输出里 `round<N>-*` 前缀解析的 N（worktree 一创建分支就带 N，docs 目录还没建也能防撞）；
   3. **其它 worktree 的 docs**：`git worktree list --porcelain` 遍历每个 worktree 路径，扫其 `docs/<N>-*` 解析 N（覆盖「worktree 内已建 docs 目录」）。
   4. **远端已合入的 docs**：`git ls-tree --name-only origin/<主分支> docs/` 解析出的 N —— 覆盖别的设备已经做完并合入的轮次。
   5. **远端在途分支**：`git branch -r --list 'origin/round*'` 解析出的 N —— ② 的远端对应物（② 只看得见本机分支），与 ④ 同吃第 1 步那次 fetch，零额外成本。

   五源并集取 max + 1。**解析失败一律跳过该条、不报错**——非 `round<N>-` 规范的分支（如自由描述分支、`feat/xxx`）、worktree 路径不可达等都跳过，不阻断开轮。**fetch 失败时 ④⑤ 整体缺席**，按本地三源算并明确提示（见「远端对齐」的降级表）。

3. **确定本轮中文描述**：issue 驱动 → 复用第 1 步已拉到的 issue 详情，从 issue 标题提炼简短中文描述；自由描述 → 从描述文字提炼。
4. **创建 worktree**（默认；带 `--no-worktree` 时跳过本步）—— 见下方「worktree 创建」小节。
5. 在 `docs/` 下创建开发项文件夹 `docs/<N>-<中文描述>/`（worktree 模式下落在新 worktree 内）。
6. 基于参数撰写 `PROMPT.md`（两个分支具体行为见下）。
7. 进入计划模式，撰写 `PLAN.md` 并请用户确认 —— 见下方「PLAN 撰写：外部行为断言先实证」小节。
8. 用户确认后再开始写代码。

#### 远端对齐（通用流程第 1 步展开）

**为什么**：多设备 + 云端 routine 并行的仓库里，「这个需求远端早就做完了」是常态而非意外。`/start` 若完全不碰远端，撞车只会在 `/finish` 之后才暴露 —— 那时一整轮的开发与 review 已经付过钱了。（真实代价：一次完整实现 + 2 轮 review + 2 个 commit 全部作废，而远端版本还更全面。）

三步，**任何一步失败都不许阻断开轮**：

1. **`git fetch origin`** —— 只更新 remote-tracking，不动工作区、不动本地分支，安全。下面几条命令里的 `<主分支>` 按「worktree 创建」小节首条的方法探测（探一次，两处复用）。
2. **issue 驱动时，查这条是不是已经被做掉了**（自由描述分支跳过本步）：

   ```bash
   # ① issue 自身状态：走平台 API，不依赖 fetch 是否成功
   python3 $HOME/.claude/scripts/platform_issue.py issue-view <N>   # 读 state / stateReason
   # ② 关闭它的 commit —— 已合入主分支的
   git log origin/<主分支> -i -E \
       --grep '(^|[^a-z])(close[sd]?|fix(es|ed)?|resolve[sd]?) #<N>([^0-9]|$)' \
       --format="%h %ad %s" --date=short
   # ③ 同上，但只看远端在途分支（PR 已开、尚未合入）
   git log --remotes=origin --not origin/<主分支> -i -E \
       --grep '(^|[^a-z])(close[sd]?|fix(es|ed)?|resolve[sd]?) #<N>([^0-9]|$)' \
       --format="%h %ad %s" --date=short
   ```

   **这次 `issue-view` 就是「issue 驱动分支」第 1 步那一次调用，别调两遍。**

   **`--grep` 是子串匹配，两侧边界都不能省**（下面两条都是实测，别「简化」掉）：

   - **右边界 `([^0-9]|$)`** 挡住「查 `#11` 命中 `Closes #114`」—— 越小号的 issue 越容易被无关 commit 拦住。
   - **左边界 `(^|[^a-z])` + 按 GitHub 真实关键字清单枚举的动词**挡住语义相反的句子。写成 `(clos|fix|resolv)[a-z]*` 时，`still unresolved #11` 与 `not fixing #11` **都会命中** —— 把「还没修」报成「已经修完了」。GitHub 认的关闭关键字只有 close/closes/closed、fix/fixes/fixed、resolve/resolves/resolved，**没有进行时**，别用 `[a-z]*` 一把抓。

   **为什么三个信号都要**：`state` 是平台权威、且**不依赖提交信息约定** —— `/start` 要在任何项目里跑，别的项目未必写 `Closes #N`，那里 ②③ 恒为空。而 ②③ 给的是**证据**（谁做的、哪个 commit、什么时候），正是人类拍板时要看的。③ 单独存在是因为「远端分支上已经做完、PR 还开着、issue 也还 open」这类撞车 ①② 都看不见 —— 本仓 `/routine-dev` 每周开 PR 却不自动合，正是这个形态。

3. **任一命中 → 停下报告，等人类拍板**，别自己决定继续还是放弃：

   ```
   ⚠ #<N> 看起来已经被做过了：
     - issue 状态：closed（COMPLETED，2026-08-01）
     - 关闭它的 commit：735c04c 2026-08-02 fix(review-loop): …（已在 origin/master）
   选项：① 不做了（本轮取消）② 只补真增量（说明差在哪）③ 远端做得不对，重做（说明哪不对）
   ```

   **`stateReason` 是 `NOT_PLANNED` 必须单独说清**：那不是「已经做完了」，是**有人决定不做**，两者的处理方向完全相反。

**降级：三条独立的失败路径，都只提示、不阻断**

| 失败 | 处理 |
| --- | --- |
| 没有 `origin` remote（纯本地仓） | 跳过整个远端对齐，一行提示，继续 |
| `git fetch` 失败（离线 / 无权限 / 超时） | 跳过编号 ④⑤ 与 ②③，**明确打印**「远端对齐已跳过：<原因>；轮次编号与撞车检查仅基于本地信号」，继续 |
| `issue-view` 拉不到 | 照既有行为处理，不因新增的 `state` 检查而变严 |

① 走平台 API、②③ 走 git，**两条路互相独立**：一个挂了另一个照跑，别因为 fetch 失败就连 `state` 也不查了。

**撞车已经发生之后怎么办**（本地写完了才发现）不归本 skill 管 —— 判据在宪法「执行」段的停机义务里。

#### worktree 创建（通用流程第 4 步展开）

默认每轮开发在独立 git worktree 内进行，让多轮可并行、互不污染主工作树。除非 args 含 `--no-worktree`，执行：

- **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（得 `origin/master` → 取末段 `master`）；失败则本地探测 `main` / `master`。
- **防嵌套**：若当前已在某个 linked worktree 内（`git rev-parse --git-dir` ≠ `git rev-parse --git-common-dir`）→ 停下提示用户「已在 worktree 内」，问是接续当前轮还是退出，**不嵌套创建 worktree**。
- **确保 worktree 目录被忽略（优先复用全局）**：先 `git check-ignore -q .claude/worktrees` 探测是否已被忽略 —— 这会自动吃到全局 `core.excludesFile`（很多人已在 `~/.gitignore_global` 里全局忽略 `.claude/worktrees`）与任何本地规则。**已忽略 → 什么都不做**，绝不冗余落 `.claude/.gitignore`。仅当**未忽略**时，才创建 / 追加 `.claude/.gitignore` 忽略 `worktrees/`（幂等），避免主工作树把嵌套 worktree 当 untracked。
- **创建**：worktree 目录名与分支名统一为 `round<N>-<中文描述>`（`<中文描述>` 同第 5 步 docs 目录的描述）：

  ```bash
  git worktree add .claude/worktrees/round<N>-<中文描述> -b round<N>-<中文描述> <主分支>
  ```

- **进入**：`cd` 进新 worktree 目录，其后所有文件操作、git 操作都在该 worktree 内进行。
- **告知**：打印一行 worktree 路径与分支名，提示用户可在 IDE 中打开该目录并行开发。

**新 worktree 里 gitignored 的运行时依赖一概不存在**——`git worktree add` 只 checkout **tracked 文件**，于是 `node_modules/`、`.env.local` / 本地凭证、build 产物、本地缓存等在新 worktree 里全部缺失。凡在 worktree 内跑门禁 / 起服务 / 跑真机脚本都会撞上，且**与栈无关**（实测两例：前端门禁缺 `node_modules`，`tsc` / `biome` / `vite build` 因找不到 devDependency 直接炸；一次性核对脚本缺 `.env.local`，读不到云厂商 AK/SK）。两种通用应对，按依赖性质二选一：

1. **软链主 checkout**（重依赖、目录级，如 `node_modules/`）：`ln -s <主checkout>/<path> <worktree>/<path>`，**跑完即删、切勿 commit**——`node_modules/` 这类带尾斜杠的 gitignore 模式只匹配目录、**不匹配软链**，软链会以 untracked 身份冒进 `git status`。（也可选择在 worktree 内重新准备一份，如 `npm install`，代价是磁盘与时间。）
2. **回退主 checkout 路径**（只读小文件，如 `.env.local` / 凭证）：在脚本 / 工具里显式「优先 worktree 根的该文件、缺则回退主 checkout 同名文件」，比软链更轻、无残留风险。

前端场景的具体解法见 `playbooks/frontend.md` §1。

带 `--no-worktree` → 跳过本小节，在当前分支直接开发，docs 目录落在当前工作树。`/finish` 收尾时检测到非 worktree 会跳过 worktree 收尾，对称无悬空分支。

#### PLAN 撰写：外部行为断言先实证（通用流程第 7 步展开）

写 PLAN 前先扫一遍需求（含 issue 正文）里**对外部工具 / 系统行为的技术断言**（git 命令的效果、文件系统语义、网络协议、第三方 API 行为）。字面表述可能是错的、或藏着提出者自己没意识到的副作用；照抄进设计，错误假设会一路写进代码与测试，等 code review 才暴露，代价远高于事前几分钟。

- **判据**：断言涉及「会不会丢数据 / 会不会被拒绝 / 报错长什么样 / 有没有隐藏副作用」，且几分钟内可验 → 就该先验。
- **做法**：起最小临时沙盘（临时 git 仓、tmpdir、一次真实 API 调用）跑真实场景，**结论连同复现命令写进 `PLAN.md`，再据此定设计**；实证推翻断言就写明「原断言 X 实测不成立 → 改用 Y」，让人类 review 时看得见这次转向。
- **边界**：与「只有人知道的参数不得探测」（宪法·计划段）不冲突 —— 那条管的是**没有权威来源**的信息（服务地址、凭据、内部命名），探出来的「可用值」可能指向另一个系统，只能问人；这条管的是**有客观唯一答案**的外部行为，跑一遍就知道，不必问也不该猜。与 TDD 亦正交：TDD 验「我的逻辑对不对」，这条验「我对外部世界的假设对不对」。

### issue 驱动分支

参数命中 `#数字` 或上述任一平台的 issue URL 时：

1. **拉 issue 详情**（**与通用流程第 1 步「远端对齐」是同一次调用，不要调两遍**）：调 helper（自动按 `git remote get-url origin` 走 GitHub 或 GitLab）：

   ```bash
   python3 $HOME/.claude/scripts/platform_issue.py issue-view <N>
   ```

   如参数是完整 URL，先从中提取 N。**本轮若需要往该 issue 补材料（spike 结论、实测数据），走 `issue-comment --issue <N> --body-file <F>`，别直调 `gh issue comment`。**

   helper stdout 输出归一 json（GitHub 风格字段），schema 固定为：

   ```json
   {
     "number": 3,
     "title": "...",
     "body": "...",
     "url": "https://...",
     "labels": ["type:X", "area:Y", "priority:Z"],
     "state": "open",
     "stateReason": ""
   }
   ```

   GitLab 端的 `iid` / `web_url` / `description` 已在 helper 内归一为 `number` / `url` / `body`，本 SKILL 直接按上述 schema 读字段。

   `state` 两端归一后只有 `open` / `closed` 两个值（GitLab 的 `opened` 已归一为 `open`）；`stateReason` 是 **GitHub 独有**（`COMPLETED` / `NOT_PLANNED`），GitLab 端恒为空串。判不出状态时一律算 `open` —— 失败方向定死在「照常开轮」。完整契约见 `scripts/platform_issue.md`。

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
