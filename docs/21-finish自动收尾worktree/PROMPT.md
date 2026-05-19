> 来自 [#9 /finish 自动识别 worktree 并合并清理](https://github.com/pkulijing/claude-code-global/issues/9)
> Labels: `type:feat` `area:skill` `priority:P2`

# /finish 自动识别 worktree 并合并清理

## 背景

Round 20 是首次完整在 worktree 内走 round。`/finish` 完成后用户还要手工：

1. 反复跟 AI 说「合入 master 吧」→ 调 `/rebase` →（冲突时）逐个解 →（成功后）`git merge --ff-only`
2. 再单独说「清理 worktree」→ `git worktree remove` + `git branch -d` + `git tag -d backup/*`

这三步本质都是「收尾」，但当前散落在 `/finish` 之外，每步都要人机往返一次。

## 希望达到

`/finish` 在调完 `/commit` 后自动判断当前是否在 worktree 内，若是则一站式完成「rebase → FF merge → 清理」：

- 当前不在 worktree → 现状不变（finish 直接结束）
- 当前在 worktree → 自动进入「worktree 收尾」分支：
  - 自动 rebase 到主分支（master/main，由 `git symbolic-ref refs/remotes/origin/HEAD` 探测）
  - 自动 FF merge 到主分支
  - 二次确认后清理 worktree 目录 + 分支 + backup tag（销毁性动作必须确认）
  - 推送由用户决定（与 finish 现有「不自动 push」约定一致）

## 候选方向

- **方向 A（倾向）**：`/finish` 新增 `Step 6: worktree 收尾`，内部复用 `/rebase` skill 的阶段 1-3。优：复用已成熟的 rebase 流程；缺：finish 与 rebase 强耦合，rebase 改了 finish 也要跟
- **方向 B**：`/finish` 仅检测+打印提示「请跑 `/rebase`」，不做实际合并。优：实现最简；缺：等于没改，仍是三步走
- **方向 C**：抽独立 `/worktree-finish` skill，`/finish` 检测后委托。优：职责清晰；缺：多一个 skill，使用者要记多个入口

## 风险 / 注意点

- 销毁性动作（删 worktree + 删 branch + 删 backup tag）必须二次确认；用户拒绝则保留所有状态，跟当前 `/rebase` 阶段 3 一致
- rebase 冲突几乎必发（Round 20 实测 DEVTREE.md 必冲突，因为 finish 跑了 `/devtree` 更新计数行 + 节点索引，跟主分支可能并行进度撞车）→ 冲突时 finish 暂停让用户解，不自动跳过
- 不自动 push（用户对推送有掌控权）
- IDE 打开 worktree 中文件时 `git worktree remove` 可能失败 → 失败要给清晰提示让用户关闭再重试，不要硬删

## scope

单 round，改 `/finish/SKILL.md` 一处文档；复用 `/rebase` 已有阶段输出，无新工具引入；估 < 100 行 skill 文档增量。
