---
name: rebase
description: 诊断本地分支分叉并按清单引导完成 rebase，历史保持 FF 直线
disable-model-invocation: true
---

用户调用此 skill 表示当前本地有分支分叉，需要通过 rebase 把分叉整理成直线历史。

## 参数说明

调用时可附带参数（args），支持以下几种形式：

| 参数 | 含义 | 示例 |
|---|---|---|
| （无） | 把**当前分支** rebase 到 `master` 上（默认 base） | `/rebase` |
| `<base>` | 把**当前分支** rebase 到指定的 `<base>` 上 | `/rebase develop` |
| `abort` | 当前正处于 rebase 中间状态，放弃本次 rebase | `/rebase abort` |
| `continue` | 当前正处于 rebase 中间状态，解决完冲突后继续 | `/rebase continue` |

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
6. **分段确认**：每个阶段结束必须等人类确认再进下一阶段，禁止一口气跑完。

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

诊断报告中明确写出"将把 `<current>` rebase 到 `<base>`"，**停下来等人类确认后进入阶段 1**。

## 阶段 1：前置检查与备份

确认方向后，执行强制项：

1. **工作区必须干净**。不干净则要求人类先 `git commit` 或 `git stash`，不得直接进入下一步。
2. **打备份 tag**：`git tag backup/<branch-name>-$(date +%Y%m%d-%H%M)`。
   - 明确告诉人类："如果 rebase 搞砸了，用 `git reset --hard <备份 tag>` 回到此刻。"
3. 切到要被 rebase 的分支（如果 rebase 发生在 worktree 里，提醒人类 `cd` 到对应 worktree 目录）。

**停下来等人类确认后进入下一阶段。**

## 阶段 2：执行 rebase 与冲突处理

执行 `git rebase <base>`。

### 若无冲突

直接展示 `git log --graph --oneline -10`，让人类肉眼验证历史正确，然后进入阶段 3。

### 若有冲突

1. 用 `git status` 列出冲突文件。
2. **逐个文件处理，不要一次改完**。每解决完一个文件，`git add <file>`。
3. 所有冲突文件都解决完后，运行 `git rebase --continue`。
4. 若后续 commit 继续冲突，重复 1–3。
5. 随时可用 `git rebase --abort` 撤销整个 rebase。备份 tag 作为二重保险。

rebase 完成后，展示 `git log --graph --oneline -10` 让人类肉眼验证。

**停下来等人类确认历史正确后进入下一阶段。**

## 阶段 3：FF 合并 / 推送 / 验证

### FF 合并到目标分支

若本次 rebase 的目的是把分叉合回主干（如 `master`）：

1. `git checkout <target-branch>`
2. `git merge --ff-only <rebased-branch>`
3. 若 `--ff-only` 失败，说明目标分支在 rebase 期间又有新 commit。处理方式：**回到阶段 2，把 rebased-branch 继续 rebase 到最新的目标分支上**，再来一次 FF。**禁止 fallback 到普通 merge**。

### 推送（如需要）

- 被 rebase 过的分支若已推送过远程：`git push --force-with-lease origin <branch>`，**禁用 `git push --force`**。
- FF 推上去的主干分支（如 `master`）：正常 `git push` 即可。

### 验证

- 提醒人类跑测试或启动服务，确认功能未坏。
- 确认无误后，可删除阶段 1 的备份 tag：`git tag -d backup/...`。
