---
name: finish
description: 完成当前开发项：撰写 SUMMARY.md，关联并关闭 GitHub issue（如有），更新 BACKLOG.md，提交代码
disable-model-invocation: true
---

用户调用此 skill 表示当前开发项已完成。

**参数处理**：调用时可能附带参数（args），参数是用户对本次开发的额外说明，比如需要特别强调的点、遗留问题、后续 TODO 等。撰写 SUMMARY.md 时应把参数内容融入到对应章节中（如「局限性」「后续TODO」或「关键设计」）。若无参数则按常规总结即可。

执行以下步骤：

## Step 1：撰写 SUMMARY.md

按全局 CLAUDE.md「总结」部分的要求，在 `docs/` 下当前开发项文件夹中撰写 `SUMMARY.md`（结合参数内容）。

### Step 1.5：扫 SUMMARY 提示「不再追踪」段补录

写完 SUMMARY 后，扫「局限性」与「后续 TODO」段，问用户：

> 「上面有没有**刻意决定不做**的项要补到 BACKLOG.md「不再追踪」段？」

- 用户给出条目 + 原因 → 引导用户写一行追加到 `docs/BACKLOG.md` 的「## 已完成 / 不再追踪」段（每条带原因，避免未来翻老 SUMMARY 误以为是遗漏）
- 用户说「无」→ 跳过
- BACKLOG.md 不存在 → 跳过此步（issue 驱动模式由 `/backlog` 首次调用时初始化骨架）

## Step 2：识别 issue 关联与 BACKLOG.md 索引清理

读 `docs/<本轮编号>-*/PROMPT.md` 顶部，看是否有 `> 来自 [#<N> ...](<URL>)` 引用块（由 `/start <issue#>` 写入）：

- **有 issue 关联** → 提取 issue 号 `#N` 与 URL，记下用于后续：
  - 让 `/commit` 在 message body 写 `Closes #N`，commit/PR 合并到 default branch 时 GitHub 自动关 issue
  - 从 `docs/BACKLOG.md` 索引中**删除**对应 URL 那一行（无 BACKLOG.md 文件则跳过）
- **无 issue 关联**（自由描述分支） → 仅按本步骤剩余动作走，不涉及 issue/BACKLOG

## Step 3：调用 `/devtree`

调用 `/devtree` 更新开发树（`docs/DEVTREE.md`）。

## Step 4：调用 `/commit`

调用 `/commit` 提交所有变更（包括 SUMMARY.md / DEVTREE.md / 本次 BACKLOG.md 的变化）。

**关键**：如果 Step 2 识别到 issue 关联，把 `Closes #N` 作为额外上下文传给 commit skill —— 让生成的 commit message body 自然包含 `Closes #N` 这一行（不要嵌入 title）。

## Step 5：轻量提示

收尾打印一行：

> 「如果 SUMMARY 里的「后续 TODO」有想真正推进的项，单独跑 `/backlog` 起 issue。SUMMARY 是回顾文档不是承诺清单，TODO 不必每条都开 issue。」
