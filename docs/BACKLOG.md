# claude-code-global — Backlog

未来开发项的**速览索引**。每条都对应一个 GitHub Issue，**详情、讨论、跨轮上下文都在 issue 里**。

**为什么这样组织**：GitHub Issues 是真源（permanent history + 通过 `Closes #N` 跟 commit/PR 永久关联，开发完归档进 closed 仍可检索）。这个文件是当前还没开发的项的扁平快照，方便一眼扫到全图、决定下一轮挑哪个。

## 工作流

- **新增想法** → `/backlog` 走 issue templates，挂三轴 label，建完顺手在本文件相应分组里加一行
- **开新轮** → 从下面挑一条 → `/start <issue#>` 把 issue 详情贴进 PROMPT.md → 开干
- **收尾一轮** → PR / commit message 写 `Closes #<issue 号>` 自动关 issue → `/finish` 删本文件这一行

## 三轴分类约定

- **type**：`type:feat` / `type:bug` / `type:refactor` / `type:perf` / `type:test` / `type:docs`
- **area**：模块分类，按本项目 [.github/labels.yml](../.github/labels.yml) 中的 `area:*` 列表（`install` / `skill` / `hook` / `template` / `doc`）
- **priority**：`P0`（必须做、不做有重大风险）/ `P1`（重大新功能 / 用户能感知的明显问题）/ `P2`（一般小功能 / 偶发问题 / 触发面窄）

## P0 — 必须做

(暂无)

## P1 — 重大新功能

(暂无)

## P2 — 一般小功能小修复

(暂无)

## 已完成 / 不再追踪

历史已完成项**不在本文件追踪**，直接看 [closed issues with priority labels](https://github.com/pkulijing/claude-code-global/issues?q=is%3Aissue+is%3Aclosed+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2)。

下面只列**刻意决定不做**的条目（避免未来翻老 SUMMARY 误以为是遗漏）：

(暂无)
