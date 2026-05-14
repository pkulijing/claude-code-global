# Round 18：/sync-project-config 支持「无 stack 只 \_common」的 adopt 路径

> 关联 issue：[#1](https://github.com/pkulijing/claude-code-global/issues/1)（`type:feat` / `area:skill` / `priority:P2`）

## 开发项背景

为 `claude-code-global` 自己跑 `/sync-project-config` 时发现：本仓库是 bash + jq 模板源仓库，没有任何 stack 真正合身（`python-uv` 大半文件不适用），但完全可以受益于 `_common` 的 issue templates、`labels.yml`、`.prettierrc` 等 stack-无关资源。

当前 `skills/sync-project-config/SKILL.md` 强制 adopt 必选一个 stack，且 normal sync 在 2.1 硬断言 `len(stacks) == 1`，多处直接访问 `stacks[0]`。本仓库此前靠手写 marker `stacks: []` 绕过 adopt，但下次跑 normal sync 一定会被断言挡下。

希望解决：让"无 stack（只 `_common`）"成为合法路径，闭环可跑（diff → TODO → 决策 → 执行 → 写回 marker），向前兼容已有 `stacks: [{...}]` 形态项目。

## 实现方案

### 关键设计

1. **方向选择**：放宽断言 + adopt 加「无 stack」选项 + 各处 `stacks[0]` 访问加 length=0 分支。**不**把 `_common` 提升为"伪 stack 一等公民"放进 `stacks` 列表 —— 后者与既有「`_common` 永远自动应用、不显式记录」约定冲突，会牵连 schema、bootstrap、文档多处。

2. **skipped 列表的位置切换**：length == 1 时读写 `stacks[0].skipped`（原行为）；length == 0 时改读写 marker **顶层** `skipped`（新增可选字段）。两者 schema 完全一致，仅位置不同。这样设计避免在 length=0 时引入"虚拟 stack 条目"，保留「`_common` 不进 stacks」约定的语义纯净。

3. **`__subpath__` 在 length=0 项目的处理**：原则上 `_common` 不该放 `__subpath__/` 内容（无 stack 项目下没有有效 path 落点）；若违反（设计约束被破坏），按项目根 `<rel>` 兜底 + 输出警告。这是一条防御性兜底，不依赖它正常工作。

4. **`git diff` pathspec 显式分支**：length=0 时只传 `templates/_common/`，**不**省略 pathspec —— 否则 `git diff` 会扫全 templates、误把其他 stack 的变更带进来。

### 开发内容概括

改了 2 个文件，新增 1 个 docs 目录：

- **`skills/sync-project-config/SKILL.md`**（8 段加 length=0 分支）：
  - 顶部 overview 加「两种项目形态」说明
  - 2.1 解析 marker：断言改 `len(stacks) ≤ 1`，length=0 时改读顶层 `skipped`
  - 2.3 计算模板变更：`git diff` pathspec 显式分支，length=0 时只扫 `_common/`
  - 2.4 四象限分析：`__subpath__` 在 length=0 时的兜底说明
  - 2.5 skipped 持久化：读取位置随 length 切换
  - 4.2 用户选 stack：`AskUserQuestion` 选项列表追加「无 stack（只 \_common）」
  - 4.3 全套用模板：length=0 时模板源只剩 `_common`
  - 6 / 6.1 执行 + 写回 marker：skipped 写回位置随 length 切换；adopt 写 `stacks: []` 或 `[{stack, path: ".", skipped: []}]`

- **`docs/11-跨项目共享模板与sync-skill/SCHEMA.md`**：
  - 字段定义块加顶层 `skipped`（与 `stacks[0].skipped` 互斥）
  - `stacks` 字段说明：放宽到长度 0 或 1，两种形态各自描述
  - 新增「无 stack 项目」字段段 + 完整示例块
  - `_common` 章节补述：明确 length=0 项目时 `_common` 是唯一模板来源

- **新增 `docs/18-sync支持无stack路径/`**：PROMPT.md + PLAN.md + 本 SUMMARY.md

### 额外产物

无（纯 prose / schema 文档改动，本轮无可执行代码、无单测、无脚本）。

dogfood 验证由 `~/.claude/global-repo` 软链 + `install.sh` 重跑后用户自行触发 `/sync-project-config` 完成，不在本轮 PR 范围。

## 局限性

1. **未实测 dogfood**：`~/.claude/skills/sync-project-config/` 软链指向主仓库的 `skills/` 路径，本轮改动在 worktree 分支中，merge + 重跑 `install.sh` 后才会生效。本轮没有"先 merge 再回归验证"步骤，依赖用户实际跑一次 `/sync-project-config` 触发 normal sync 闭环来兜底。

2. **skipped 顶层 vs `stacks[0]` 位置切换的边界用例未穷举**：如果用户半路把 marker 从 `stacks: []` 改成 `stacks: [{...}]`（或反向），原本顶层 `skipped` 的条目可能"消失"（被新断言下 sync 跳过）。未在 SKILL.md 中明示这种迁移路径的兼容处理；当前依赖"用户手动迁移 marker"。

3. **`__subpath__` 在 length=0 下的兜底行为**只是写在 SKILL.md prose 里，没有代码 enforce。如果哪天有人把 `_common` 里塞了 `__subpath__/` 文件，sync 会按警告 + 项目根兜底落，行为依赖 AI 严格读 SKILL.md prose。

## 后续 TODO

- 等本轮 merge + `install.sh` 重跑后，**在本仓库实跑一次 `/sync-project-config`** 走 normal sync 路径（marker 已是 `stacks: []` 形态），确认闭环：模板未变 → 跳过；模板有变 → TODO 清单 → accept/skip → 写回顶层 `skipped`、`template_commit` 更新。这是最直接的 dogfood 验收。
- 多 stack monorepo 支持（schema 已设计、未实现） —— 与本轮 length=0 在断言层共享同一个放宽（`<= 1` → `<= N`），但项目侧落点（`<stacks[i].path>/<rel>`）需要新逻辑。可作为独立 round。
- `/bootstrap` 是否要对称地加「无 stack」选项？现状 `/bootstrap` 也强制选 stack，理论上同样问题。本轮没动 `/bootstrap` —— 它的核心场景是空项目首次落模板，"无 stack 空项目"几乎不存在合理用法。但如果未来出现，可补一条独立 issue。
