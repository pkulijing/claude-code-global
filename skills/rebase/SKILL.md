---
name: rebase
description: 诊断本地分支分叉并按清单引导完成 rebase，历史保持 FF 直线
disable-model-invocation: false
---

用户调用此 skill 表示当前本地有分支分叉，需要通过 rebase 把分叉整理成直线历史。

## 参数说明

调用时可附带参数（args），支持以下几种形式：

| 参数       | 含义                                              | 示例               |
| ---------- | ------------------------------------------------- | ------------------ |
| （无）     | 把**当前分支** rebase 到 `master` 上（默认 base） | `/rebase`          |
| `<base>`   | 把**当前分支** rebase 到指定的 `<base>` 上        | `/rebase develop`  |
| `abort`    | 当前正处于 rebase 中间状态，放弃本次 rebase       | `/rebase abort`    |
| `continue` | 当前正处于 rebase 中间状态，解决完冲突后继续      | `/rebase continue` |

**要求**：

- 当前分支必须是**要被 rebase 的分支**（而不是 base 本身）。若当前分支就是 base（例如无参时当前分支是 `master`），立即停下告知人类。
- 若人类想整理另一条分支，应先自行切到那条分支（或在对应 worktree 内调用）。
- `abort` / `continue` 只在 `.git/rebase-*` 存在时才有效；若当前没有进行中的 rebase，应告知人类并退出。
- 无论是否带参数，**阶段 0 的诊断步骤都要跑**，让人类看到状态再动手。

## 核心原则（违反任一原则都应立刻停下来问人类）

1. **只处理本地**：不执行 `git fetch` / `git pull`。远程同步由人类在调用前自行完成。
2. **所有合并必须 FF**：严禁生成 merge commit。rebase 完成后用 `git merge --ff-only`；若 FF 失败，继续 rebase 直到能 FF，**绝不 fallback 到普通 merge**。
3. **个人分支才 rebase**：如果要被 rebase 的分支是 `master` / `main`、或是已被他人 review 的公共分支，立即停下问人类。
4. **数据优先于直线历史**：一旦出现看不懂的状态，宁可 `git rebase --abort` + `git reset --hard <备份 tag>` 回退，也不要强行推进。
5. **不支持交互式 rebase**：不使用 `-i`；如需合并/重排 commit，请人类手动处理。
6. **默认静默直行，风险才停（risk gates）**：诊断方向明确且无风险时，诊断 → 备份 → rebase → FF 合并**一气呵成、不逐阶段等确认**，末尾汇报结果即可。无冲突的 rebase 本该近乎瞬间完成，不该被反复「停下 → 等 OK」拖住。**仅在命中下面这份「必停清单」时才停下、说明原因、等人类决策**：
   - 分叉方向不明 / 诊断看不清；
   - 当前分支就是 base（如无参时当前分支是 `master`）；
   - 要 rebase 的是 `master` / `main` 或已被他人 review 的公共分支（呼应原则 #3）；
   - 工作区不干净；
   - rebase 出现**冲突**；
   - FF `git merge --ff-only` 失败；
   - 需**推送到远程**（`git push --force-with-lease` 或推主干）—— 高影响，即便前面全程无冲突也停一次确认，**绝不静默 force push**；
   - 出现任何看不懂 / 意外的状态。

   不在清单内（诊断清楚且方向明确、工作区干净、rebase 无冲突、FF 成功）→ **直接继续，不打断人类**。注意：静默直行绝不牺牲安全 —— 原则 #4「数据优先于直线历史」不变，阶段 1 的备份 tag **无条件必打**，静默直行也不例外。

## 阶段 0：诊断当前状态

执行以下命令并展示结果：

- `git rev-parse --show-toplevel`
- `git worktree list` — 识别当前是否在 worktree 内，属于哪一个
- `git branch --show-current` — 当前分支
- `git status` — 工作区 / 暂存区是否干净
- `git log --graph --oneline --all -20` — 可视化本地分叉

基于结果输出一份**诊断报告**，至少包含：

- 当前位于哪个目录 / worktree / 分支
- 工作区是否干净
- 是否已处于进行中的 rebase（检查 `.git/rebase-merge` 或 `.git/rebase-apply`）
- 识别出的分叉：哪两条分支从哪个 commit 开始分开，各自有几个 commit
- 建议的 rebase 方向（例如"把 `feat/installsh` 的 3 个 commit rebase 到 `master` 上"）

根据参数与诊断结果分流：

- **`abort` / `continue`**：确认确实在 rebase 中间状态后，执行 `git rebase --abort` 或 `git rebase --continue`，完成后跳到阶段 3（若 continue 完成）或直接结束（若 abort）。
- **带 `<base>` 参数**：采用该 base 作为目标。
- **无参数**：默认以 `master` 作为 base。**若当前分支就是 `master`，立刻停下告知人类**，不要试图去找"另一条该 rebase 的分支"。

诊断报告明确写出"将把 `<current>` rebase 到 `<base>`"。方向明确且未命中必停清单（原则 #6）→ 直接进阶段 1，无需等确认；命中必停项 → 停下说明原因、等人类决策。

## 阶段 1：前置检查与备份

确认方向后，执行强制项：

1. **工作区必须干净**。不干净则要求人类先 `git commit` 或 `git stash`，不得直接进入下一步。
2. **打备份 tag**：`git tag backup/<branch-name>-$(date +%Y%m%d-%H%M)`。
   - 明确告诉人类："如果 rebase 搞砸了，用 `git reset --hard <备份 tag>` 回到此刻。"
3. 切到要被 rebase 的分支（如果 rebase 发生在 worktree 里，提醒人类 `cd` 到对应 worktree 目录）。

工作区干净 → 打完备份 tag 直接进阶段 2，无需等确认；工作区不干净 → 停下（命中必停清单），要求人类先 `git commit` / `git stash`。

## 阶段 2：执行 rebase 与冲突处理

执行 `git rebase <base>`。

### 若无冲突

展示 `git log --graph --oneline -10` 备查，**直接进入阶段 3，不停顿**。

### 若有冲突

1. 用 `git status` 列出冲突文件。
2. **逐个文件处理，不要一次改完**。每解决完一个文件，`git add <file>`。
3. 所有冲突文件都解决完后，运行 `git rebase --continue`。
4. 若后续 commit 继续冲突，重复 1–3。
5. 随时可用 `git rebase --abort` 撤销整个 rebase。备份 tag 作为二重保险。

rebase 完成后展示 `git log --graph --oneline -10` 让人类肉眼验证。**冲突属必停项**（原则 #6）：解决过程与解决完都停下过目，确认历史正确再进阶段 3。

## 阶段 3：FF 合并 / 推送 / 验证

### FF 合并到目标分支

若本次 rebase 的目的是把分叉合回主干（如 `master`）：

1. `git checkout <target-branch>`
2. `git merge --ff-only <rebased-branch>`
3. 若 `--ff-only` 失败，说明目标分支在 rebase 期间又有新 commit。**FF 失败属必停项**：停下告知人类，处理方式是**回到阶段 2，把 rebased-branch 继续 rebase 到最新的目标分支上**，再来一次 FF。**禁止 fallback 到普通 merge**。

FF 成功则**直接继续**，不停顿。

### 推送（如需要）

**推送属必停项**（原则 #6）：无论 `--force-with-lease` 还是推主干都高影响，推送前必停一次、告知推什么、等人类点头，绝不静默 force push。

- 被 rebase 过、已推过远程的分支：`git push --force-with-lease origin <branch>`，**禁用 `git push --force`**。
- FF 推上去的主干（如 `master`）：正常 `git push`。
- 纯本地无需推送 → 跳过本节。

### 验证

- 静默直行跑完后，给一份**结果汇报**：走了哪几个阶段、备份 tag 名、最终 `git log --graph --oneline -10`、是否已 / 待推送。
- 提醒人类跑测试或启动服务，确认功能未坏。
- 确认无误后，可删除阶段 1 的备份 tag：`git tag -d backup/...`。

### round 编号一致性检查（仅用 `docs/<N>-...` 轮次目录的仓库）

rebase / 历史整理后目标分支可能已占用本地 round 编号，导致三处脱节。**触发**：目标分支已占用当前 round 编号，或 docs round 与 commit round 不一致时，逐条核对、命中给**顺延计划并要求确认**、绝不静默：

1. `docs/<N>-...` 目录编号顺延到下一个空位。
2. `docs/DEVTREE.md`（Epic 结构 / 可视化 / 节点索引）随之同步顺延。
3. commit message `[round N]` 前缀与目录编号一致。
4. **顺延如需改写已提交历史**（rename docs + amend/rebase）→ 明确提示「这会改写历史」、等确认再动手。
5. 顺延后重跑 `git log --oneline` / `git status` 确认三者一致。

纯代码仓（无 `docs/<N>-...`）→ 跳过本节。
