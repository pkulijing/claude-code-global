> 来自 [#4 /finish skill 收尾时同步 review/更新 README](https://github.com/pkulijing/claude-code-global/issues/4)
> Labels: `type:feat` `area:skill` `priority:P2`

## 优先级判断

触发面窄（只在 `/finish` 时生效）、不做不会破功能；但 README 漂移已经在本仓库实际发生（缺 skill、没说模板），属于积累型小问题，归 P2。

## 动机

`README.md` 是给人类看的项目门面文档，但当前没有任何机制保证它跟得上项目实际状态。本仓库 README 已经明显滞后 —— 缺很多 skill、完全没提模板系统。根因是 `/finish` 这个收尾入口没把 README 纳入 review 范围。

**当前漂移的具体例子**（见 `README.md`）：

- 「Skills」段只列了 `/start` `/finish` `/commit` 三个，实际仓库 `skills/` 下有十几个（`/backlog`、`/rebase`、`/pybump`、`/devtree`、`/bootstrap`、`/sync-project-config`、`/perm-prune` 等）
- 完全没提模板系统（`templates/_common/`、stack 模板、`/sync-project-config` 工作流）
- 完全没提 hook 系统（`hooks/`、`format-after-edit.sh` 等）
- 没提 BACKLOG / issue 驱动工作流
- 没提 docs 目录结构与四步开发模式

## 希望达到

每轮开发收尾跑 `/finish` 时，主动 review README 与本轮变更的相关性，必要时同步更新。判断规则要清晰，避免无关变更也强行编辑 README 制造噪音。

## 候选方向

- **方向 A**：`/finish` 流程末尾加一步 "review README"，AI 读当前 README + 本轮 diff，自行判断是否需要更新；要更新则直接编辑，不需要则一句话告知用户跳过。
  - 优点：简单
  - 缺点：判断标准不明确容易过度/欠更新
- **方向 B（倾向）**：方向 A 基础上加明确判断准则 —— 仅当本轮变更涉及以下情形才触发 README 更新：
  - 新增 / 删除 skill
  - 新增 / 删除 hook
  - 目录结构变化
  - 面向用户的工作流改动（如 BACKLOG 工作流、安装方式、模板系统）

  纯内部重构、bug fix、文档微调（非 README）不触发。
  - 优点：信号明确，可预测
  - 缺点：清单要维护

## 风险 / 注意点

- **误判触发**：每次都改 README 会让 commit 噪音变大
- **误判跳过**：长期积累又回到现状
- **与 `/finish` 现有流程的顺序**：现状是 SUMMARY → 1.5 不再追踪 → BACKLOG 清理 → devtree → commit。建议放在 SUMMARY 之后、commit 之前（≈ 现 Step 3 与 Step 4 之间），让 README 改动跟本轮代码进同一 commit

## Scope

- 改 `skills/finish/SKILL.md`：加一步 README review，附明确触发条件清单
- 视情况在本仓库**先手工把 README 补到最新状态**作为基线（避免 skill 上线第一次跑就要 diff 一大坨历史漂移）
- 估约 0.5 ~ 1 轮
