> 来自 [#1 /sync-project-config 支持「无 stack 只 \_common」的 adopt 路径](https://github.com/pkulijing/claude-code-global/issues/1)
> Labels: `type:feat` `area:skill` `priority:P2`

## 背景

为 `claude-code-global` 自己跑 `/sync-project-config` 时发现：本仓库是 bash + jq 模板源仓库，没有任何 stack 真正合身（`python-uv` 大半文件不适用），但完全可以受益于 `_common` 的 issue templates、`labels.yml`、`.prettierrc` 等 stack-无关资源。

当前 `skills/sync-project-config/SKILL.md` 的约束：

- **adopt 模式 4.2**：强制让用户用 `AskUserQuestion` 选一个 stack，没有「无 stack（只 \_common）」选项
- **normal sync 2.1**：硬断言 `len(stacks) == 1`，不允许 0
- **后续步骤**：2.4 / 2.5 / 6 / 6.1 多处直接访问 `stacks[0]`，假定一定存在

本仓库本次靠手写 marker `stacks: []` 绕过 adopt，但下次跑 normal sync 一定会被 2.1 断言挡下。

## 希望达到

让"无 stack（只 \_common）"成为合法路径，**对模板源仓库自身、以及任何确认所有现成 stack 都不合身的项目**都可以用。具体：

- adopt 模式 4.2 在 `AskUserQuestion` 里加一条「无 stack（只 \_common）」选项；用户选这条后，跳过"选 stack"语义，仅自动应用 `_common`
- normal sync 2.1 断言改成 `len(stacks) <= 1`（允许 0）
- 所有后续访问 `stacks[0]` 的路径（2.4 path 计算、2.5 skipped 处理、6 节执行写回 skipped、6.1 marker 回写）加 length=0 分支
- marker 写出 `stacks: []` 时 sync 能正常跑完闭环（diff → TODO → 决策 → 执行 → 写回 marker，全程仅 `_common` 来源）
- 文档：`docs/11-跨项目共享模板与sync-skill/SCHEMA.md` 加 length=0 示例和 `_common`-only 形态说明

## 候选方向

- **方向 A（倾向）**：放宽断言 + 在 adopt 加「无 stack」选项 + 各处加 length=0 分支。与现有「`_common` 永远自动应用、不进 `stacks` 列表」约定一致
- **方向 B**：把 `_common` 也作为"伪 stack"放进选项里、与 stack 平级。语义更对称，但与现有「`_common` 不显式记录」约定冲突，需要顺带改 schema、影响范围大

倾向 A：增量小、向前兼容、与既有约定一致。

## 风险 / 注意点

- 已 bootstrap 项目的 marker 仍是 `stacks: [{...}]` 形态 → 必须向前兼容
- 文档同步：SCHEMA.md 需要补 length=0 形态说明 + 示例
- 本仓库自身就是 dogfood 用例：改完先在本仓库跑一次 `/sync-project-config` 验证闭环

## Scope

- **改动文件**：
  - `skills/sync-project-config/SKILL.md`
  - `docs/11-跨项目共享模板与sync-skill/SCHEMA.md`
- **不需前置 spike**
- **估时**：1 小时内
