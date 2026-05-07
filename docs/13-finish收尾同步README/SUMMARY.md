# SUMMARY：/finish 收尾时同步 review/更新 README

## 开发项背景

来自 [#4 /finish skill 收尾时同步 review/更新 README](https://github.com/pkulijing/claude-code-global/issues/4)（`type:feat` `area:skill` `priority:P2`）。

**希望解决的问题**：`README.md` 是项目门面文档，但当前没有任何机制保证它跟得上仓库实际状态。本仓库 README 已经明显滞后 —— 只列了 `/start /finish /commit` 三个 skill（实际有十个），完全没提 hooks 系统、模板系统、BACKLOG / issue 驱动工作流。根因是 `/finish` 这个收尾入口没把 README 纳入 review 范围。

## 实现方案

### 关键设计

- **方向 B（清单触发）**：仅当本轮变更命中预设清单才触发 README review；纯内部重构 / bug fix / 文档微调不触发。比方向 A（每次都自行判断）信号明确、可预测。
- **插入位置 Step 3.5**：放在 Step 3（`/devtree`）之后、Step 4（`/commit`）之前，让 README 改动跟本轮代码进同一 commit；不重排原有 Step 编号，避免影响外部引用。
- **数据源边界**：`git status --porcelain` + `git diff --cached --name-status` 并集，**明示忽略**前面几步刚改的 `SUMMARY.md` / `DEVTREE.md` / `BACKLOG.md` 自身 —— 它们不该触发 README review，否则每次 finish 都会循环触发。
- **一次性基线补齐**：本轮顺手把 README 补到最新（hooks / 模板 / 全量 skill 表 / BACKLOG 工作流），避免 skill 上线第一次跑就要 diff 一大坨历史漂移。

### 开发内容概括

- `skills/finish/SKILL.md` — 在 Step 3 与 Step 4 之间新增 **Step 3.5：README review & update**，含触发清单（skill / hook 增减、顶层目录变化、面向用户的工作流改动）、明示不触发清单、判定数据源、忽略项、触发后子步
- `README.md` — 一次性基线补齐：
  - 顶部一句话补 hooks/templates，加四步开发模式 + issue 驱动 pointer
  - 「工作原理」表新增 `hooks/*` / `templates/` / 仓库根目录三行
  - 「GLOBAL_CLAUDE.md 内容概览」表新增 Backlog/开发项管理、跨项目共享配置两行
  - 「Skills」段拍平为单一表格，全部 skill 同级展示（之前 `/start /finish /commit` 详写 + 其他简列的分层依用户反馈被去掉了）
  - 新增「Hooks」「跨项目共享模板」「Backlog 与开发项管理」三段
- `docs/13-finish收尾同步README/` — 留档 PROMPT.md / PLAN.md / SUMMARY.md（本文件）

### 额外产物

- 无可执行代码改动 → 无单测；本任务的验证形态是 dogfood：本轮 `/finish` 调用本身就触发 Step 3.5（命中触发条件 4「面向用户的工作流改动」），自检 README 是否还需再调整

## 局限性

1. **跨多轮累积漂移仍漏**：每轮单独看都不触发，但合起来 README 仍可能慢慢落后。本轮的触发清单是「单轮命中」逻辑。
2. **触发条件 4「面向用户的工作流改动」边界依赖 AI 判断**：方向 B 已比 A 收敛了大头，但「是否算面向用户的入口/约定改了」仍有模糊边界。
3. **多语言**：当前 README 中文，未来若加英文版需扩展 review 范围。

## 后续 TODO

- 定期跑「README 全量 review」补漏：作为对单轮触发逻辑的兜底 —— 可作为新 issue（看是否真有刚需再开）
- 同样的 README 漂移风险存在于 `GLOBAL_CLAUDE.md` —— 它也是面向人类的规范文档，可能需要类似机制（但 `GLOBAL_CLAUDE.md` 改动频率低于 README，优先级更低）
