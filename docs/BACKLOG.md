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

- [#5 python-uv 模板首次接入时自动 bootstrap 项目](https://github.com/pkulijing/claude-code-global/issues/5) · `type:feat` `area:template` —— 模板核心可用性问题，sync 完还要手敲 4 步（uv init / dev deps / 装 pre-commit / pre-commit install）才能开发，体验断裂

## P2 — 一般小功能小修复

- [#1 /sync-project-config 支持「无 stack 只 \_common」的 adopt 路径](https://github.com/pkulijing/claude-code-global/issues/1) · `type:feat` `area:skill` —— 当前断言挡住 stacks=[] 的 marker，本仓库 dogfood 时手写绕过，需正式支持
- [#6 /finish 收尾时主动识别「可沉淀项」并提醒用户](https://github.com/pkulijing/claude-code-global/issues/6) · `type:feat` `area:skill` —— 让单轮经验（模板字段 / 新工作流 / 项目级 skill）能被稳定捡起，不再散落在 SUMMARY 后续 TODO 里靠人主动捞
- [#7 将 skills/hooks 转型为 Claude Code 原生 plugin，install.sh 退化为环境初始化](https://github.com/pkulijing/claude-code-global/issues/7) · `type:refactor` `area:install` —— plugin 化让日常迭代自动分发到所有设备，install.sh 瘦身到 permissions / GLOBAL_CLAUDE / scheduler 这三件 plugin 装不了的事；实测确认 plugin skill description 进 context，关键词触发不受损

## 已完成 / 不再追踪

历史已完成项**不在本文件追踪**，直接看 [closed issues with priority labels](https://github.com/pkulijing/claude-code-global/issues?q=is%3Aissue+is%3Aclosed+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2)。

下面只列**刻意决定不做**的条目（避免未来翻老 SUMMARY 误以为是遗漏）：

- **平台双兼容下的「对端死文件清理」opt-out**（`area:template`）—— round 14 决定项目根永久同时落 GitHub + GitLab 两套文件，不引入 `.cc-template.yml` 的 `platforms: [...]` 字段或类似 opt-out 机制。代价：GitHub 项目里有 4 个 `.gitlab/...` 死文件、反之亦然。理由：成本（marker schema 变更 + bootstrap/sync 多一层过滤逻辑）大于收益（仅减 4 个对端不读取的死文件）。详见 [docs/14-模板支持GitLab双轨/SUMMARY.md](14-模板支持GitLab双轨/SUMMARY.md) §5.3
