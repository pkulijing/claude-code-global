# worktree 收尾细则（`/finish` Step 8 展开）

> `/finish` Step 8 在**确认自己处在 linked worktree 内**之后读本文。非 worktree 轮（含 `--no-worktree`）根本走不到这里。

收尾流程遵循 `/rebase` 的核心原则（FF-only、备份 tag、冲突逐文件解、abort 兜底、分段确认），但**不调用 `/rebase`** —— 它阶段 3 的 `git checkout <主分支>` 在 worktree 下必失败（主分支已被主工作树占用），FF merge 必须改用 `git -C <主工作树> merge`。

## 8.1 诊断

展示 `git worktree list`、`git branch --show-current`、`git status`（应干净，`/commit` 刚跑完）、`git log --graph --oneline -15`。

- **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（得 `origin/master` → 取末段）；失败则本地探测 `main` / `master`。
- **算主工作树路径**：`dirname "$(git rev-parse --path-format=absolute --git-common-dir)"`

**前置检查**：当前分支不能就是主分支；工作区必须干净。任一不满足 → 停下问用户。

## 8.2 备份 + rebase

> `--no-rebase` 跳过本整节（不打备份 tag、不 rebase），直接进 8.3。

1. **备份 tag**：`git tag backup/<分支名>-$(date +%Y%m%d-%H%M)`，告诉用户「搞砸了用 `git reset --hard <该 tag>` 回退」。
2. **rebase**：`git rebase <主分支>`。
   - **无冲突** → 展示 `git log --graph --oneline -10`，停下等用户确认后进 8.3。
   - **有冲突**（finish 跑过 `/devtree`，`DEVTREE.md` 几乎必与主分支的并行进度撞车）→ `git status` 列冲突文件，**逐个解、逐个 `git add`**，再 `git rebase --continue`；后续 commit 续冲突则重复。**冲突时暂停让用户解，不自动跳过**；随时可 `git rebase --abort` + 备份 tag 兜底。解完展示 graph，停下等用户确认。

## 8.3 FF merge 到主分支

> `--no-merge` / `--keep-branch` 跳过本节与 8.4，改走 8.4-skip。

主分支 checkout 在主工作树，当前 worktree 不能 `git checkout` 它，故用 `-C` 在主工作树内合并：

```bash
git -C <主工作树> merge --ff-only <当前分支>
```

`--ff-only` 失败（主分支在本轮期间又前进）→ 回 8.2 把当前分支继续 rebase 到最新主分支再重试（`--no-rebase` 下不能自动 rebase → 停下提示用户去掉该开关重跑或手动 rebase）。**禁止 fallback 普通 merge。**

## 8.4 二次确认 + 清理

向用户**明确列出**将删除的项，等用户确认（销毁性动作）。`--keep-backup` 时 backup tag 不在删除列表里。

**用户确认** → 先 `cd <主工作树>`（当前 cwd 即将随 worktree 一起消失），再依次：

```bash
git worktree remove <当前 worktree 路径>
git branch -d <当前分支>
git tag -d backup/<分支名>-<时间戳>   # --keep-backup 时跳过，末尾打印保留的 tag 名
```

`git worktree remove` 失败（IDE / 编辑器占用 worktree 内文件）→ 提示「请关闭打开该目录的编辑器后重试」，**不加 `--force` 硬删**，保留全部状态。

**用户拒绝** → 保留 worktree / 分支 / backup tag 全部状态，打印当前状态，结束。

## 8.4-skip（`--no-merge` / `--keep-branch` 专用）

不 merge、不删除任何东西。打印三项的保留位置供后续手动处理：

```
本轮已 commit + SUMMARY 就位，按 --no-merge 保留：
  worktree : <当前 worktree 路径>
  分支     : <当前分支>（已 rebase 到 <主分支>，线性可后续 FF）
  backup   : backup/<分支名>-<时间戳>
后续可：① 让人 review / 提 PR；② 继续在此 worktree 迭代；③ 准备好后手动
   git -C <主工作树> merge --ff-only <当前分支> 并清理。
```

然后直接进 Step 9（跳过 8.5 —— 主分支未前进）。

## 8.5 不自动 push

打印一行提示：主分支已 FF 前进，是否 `git push` 由用户决定（与 finish 不自动 push 的约定一致）。
