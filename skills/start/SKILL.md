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

1. **远端对齐**（`git fetch` + 撞车检查）。**必须排在最前**：轮次编号要用远端信号；而撞车检查得赶在建 worktree / 建 docs 之前，否则拦下来时已经落了一个分支和一个目录要清。两条硬规则不因走哪条分支而变：**任何一步失败都只提示、不阻断开轮**；**撞车信号任一命中就停下报告、等人类拍板**，别自己决定继续还是放弃。

   - **issue 驱动轮** → **读 `references/remote-align.md`**，按其三步走完（fetch → 三信号查这条是不是已经被做掉了 → 命中就停下报告）。
   - **自由描述轮** → 没有可查的 issue、撞车检查整体不适用，只跑一条 `git fetch origin` 把远端信号取回来供第 2 步编号用（无 `origin` 或 fetch 失败 → 打印一行原因、按本地三源算，继续开轮），不必读该文件。
2. **确定轮次编号 N**：取「已占用编号」并集的最大值 +1。**为什么要并集**：并行多 round 各在独立 worktree、未合回主分支时，新建的 `docs/<N>-*` 尚未合入、本树看不见，只扫本树 `docs/` 会让各 round 算出同一个 N+1，合入时撞车；而多设备 / 云端 routine 并行时，**本地信号还会整体滞后于远端**。故五个信号源取并集：
   1. **本树 `docs/`**：现有 `docs/<N>-*` 目录名解析出的 N；
   2. **在途分支名**：`git branch --list 'round*'` 输出里 `round` 后**紧跟的数字段**即 N —— 只认数字、不管后面跟什么，于是 `round<N>-<英文短描述>` / 裸 `round<N>` / 历史的 `round<N>-<中文描述>` 三种形态通吃（worktree 一创建分支就带 N，docs 目录还没建也能防撞）；
   3. **其它 worktree 的 docs**：`git worktree list --porcelain` 遍历每个 worktree 路径，扫其 `docs/<N>-*` 解析 N（覆盖「worktree 内已建 docs 目录」）。
   4. **远端已合入的 docs**：`git ls-tree --name-only origin/<主分支> docs/` 解析出的 N —— 覆盖别的设备已经做完并合入的轮次。
   5. **远端在途分支**：`git branch -r --list 'origin/round*'` 解析出的 N —— ② 的远端对应物（② 只看得见本机分支），与 ④ 同吃第 1 步那次 fetch，零额外成本。

   五源并集取 max + 1。**解析失败一律跳过该条、不报错**——非 `round<N>` 规范的分支（如自由描述分支、`feat/xxx`）、worktree 路径不可达等都跳过，不阻断开轮。**fetch 失败时 ④⑤ 整体缺席**，按本地三源算并明确提示（见 `references/remote-align.md` 的降级表）。

3. **确定本轮中文描述**：issue 驱动 → 复用第 1 步已拉到的 issue 详情，从 issue 标题提炼简短中文描述；自由描述 → 从描述文字提炼。
4. **创建 worktree**（默认；带 `--no-worktree` 时跳过本步）—— **读 `references/worktree-create.md`** 按其执行（探测主分支 / 防嵌套 / 忽略 worktree 目录 / 撞号复核 / 创建 / 进入 / 告知 / 缺失的 gitignored 依赖怎么补）。两条硬约束先记住：分支名与 worktree 目录名统一为 `round<N>-<英文短描述>` 且**整串纯 ASCII**；**建之前必须复核这个 N 没被本地或远端占走**，占了就重算 N，别靠换个描述词绕开。
5. 在 `docs/` 下创建开发项文件夹 `docs/<N>-<中文描述>/`（worktree 模式下落在新 worktree 内）。
6. 基于参数撰写 `PROMPT.md`（两个分支具体行为见下）。
7. 进入计划模式，撰写 `PLAN.md` 并请用户确认 —— 见下方「PLAN 撰写：外部行为断言先实证」小节。
8. 用户确认后再开始写代码。

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

   helper stdout 是归一 json（GitHub 风格字段）：`number` / `title` / `body` / `url` / `labels` / `state` / `stateReason` —— 两端的字段名差异已在 helper 内抹平，本 SKILL 直接按这些名字读。**schema 与 `state` / `stateReason` 的取值语义，单一真源是 `scripts/platform_issue.md`，此处不复述**；本步只需记住一条结论：**判不出状态一律算 `open`**，失败方向定死在「照常开轮」。

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
