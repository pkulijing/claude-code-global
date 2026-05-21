# Round 23：/finish 跨项目反思可沉淀流程并直接给 claude-code-global 提 issue

> 来自 [#6 /finish 收尾时主动识别「可沉淀项」并提醒用户](https://github.com/pkulijing/claude-code-global/issues/6)
> Labels: `type:feat` `area:skill` `priority:P2`

## 背景

每个开发轮里常会冒出"值得复用"的经验 —— 可能是 `~/.claude/templates/` 里能加的字段、claude-code-global 项目可新增的 skill / hook、或某个具体项目里值得抽成 skill 的多步操作。目前这些经验只散落在对话或 SUMMARY 的「局限性 / 后续 TODO」段里，靠人主动捡，容易错过抽象时机。

原始 issue #6 把这件事定位在 **claude-code-global 自身** `/finish` 时往 SUMMARY 写一段「可沉淀项」+ 打印提醒（方向 A，< 50 行）。发起人在开发前补充澄清，把范围放大（见 issue #6 评论 / 下方「细化后的需求」）。

## 细化后的需求（发起人澄清，覆盖原始描述）

希望达到的效果：

1. 在**任意项目**里调用 `/finish` 时，反思本轮开发过程中有没有可沉淀下来的**重复性流程**；
2. 对判定值得沉淀的项，**直接向 `claude-code-global` 仓库提 issue**（跨仓库），而不只是在本地 SUMMARY 里提醒；
3. 这类 issue **不进 `claude-code-global` 的 `docs/BACKLOG.md`** —— 因为它不是在 claude-code-global 项目内部发起的，BACKLOG 只索引「本项目内发起的待办」。

## 候选去向（两路）

- **跨项目资产** → 跨仓库提 issue 到 claude-code-global：
  1. 改 `~/.claude/templates/` 下的共享模板
  2. 在 claude-code-global 里新增 skill / hook / 写进 `GLOBAL_AGENTS.md`
- **仅对当前项目有用的可复用流程** → 建议在**当前项目**里 `/backlog` 起本地 issue（不跨仓库）

## 约束与注意点

- **判定标准要明确**，避免「啥都觉得能沉淀」的噪音：跨项目通用 / 有具体落点 / 出现 ≥2 次的模式，三条尽量都满足才算候选；
- 提交 issue 是**外部可见动作**：propose → 用户确认 → 再 file，不自动提交、不阻塞 commit；用户当时不想处理可「先放一放」；
- 无候选时明示「本轮无可沉淀项」，不留空让人猜；
- 跨仓库目标 slug + platform 从 `~/.claude/global-repo`（install.sh 软链到本仓库）的 remote 动态派生，不硬编码；
- 跨仓库 issue 仍打三轴 label —— area 读 claude-code-global 自己的 `.github/labels.yml` 选取（该文件本地可读）。

## scope

比原始「方向 A < 50 行」略大：多了跨仓库 file 能力 + `platform_issue.py issue-create` 的 `--repo` 扩展。仍坚持「propose 不自动 file」保持可控、可逆。
