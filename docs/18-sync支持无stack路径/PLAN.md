# Round 18：/sync-project-config 支持「无 stack 只 \_common」的 adopt 路径

## Context

为 `claude-code-global` 自己跑 `/sync-project-config` 时发现：本仓库是 bash + jq 模板源仓库，没有任何 stack 真正合身（`python-uv` 大半文件不适用），但完全可以受益于 `_common` 的 issue templates、`labels.yml`、`.prettierrc` 等 stack-无关资源。

当前 `skills/sync-project-config/SKILL.md` 强制要求 adopt 必选一个 stack，且 normal sync 在 2.1 硬断言 `len(stacks) == 1`，多处直接访问 `stacks[0]`。本仓库本次靠手写 marker `stacks: []` 绕过 adopt，但下次跑 normal sync 一定会被断言挡下。

目标：让"无 stack（只 \_common）"成为合法路径，闭环可跑（diff → TODO → 决策 → 执行 → 写回 marker），向前兼容已有 `stacks: [{...}]` 形态项目。对应 issue #1（type:feat / area:skill / priority:P2）。

## 实现方案

采用方向 A：**放宽断言 + adopt 加「无 stack」选项 + 各处 stacks[0] 访问加 length=0 分支**。与现有「`_common` 永远自动应用、不进 `stacks` 列表」约定一致，增量最小。

### 关键认知

- "无 stack 项目" = `stacks: []`（空数组），不是 `stacks: [_common]`。`_common` 始终是隐式约定，不显式记录在 marker 里
- "无 stack" ≠ "无文件"：sync 仍要扫 `_common/`、产 TODO、写 marker
- length=0 时所有 `stacks[0].*` 访问要短路：path 默认 `.`（用 `__subpath__` 时无意义但兜底）、skipped 改读 marker 顶层临时位置

### 文件 1：`skills/sync-project-config/SKILL.md`

按章节顺序具体修改：

**2.1 解析 marker（断言放宽）**

- 改：`stacks` 列表 length 必须等于 1 → `stacks` 列表 length 必须 ≤ 1（允许 0）
- 加说明：`length == 0` 时为"无 stack（只 \_common）"项目，仅 `_common` 来源参与 sync
- `stacks[0].path` 断言保持 = `.`，但**仅当 length == 1 时才检查**

**2.3 计算模板变更（diff 命令调整）**

- 改：length == 1 时 `templates/<stack>/ templates/_common/`；length == 0 时只 `templates/_common/`
- 这是 `git diff` pathspec，传 0 路径会扫全 templates，必须显式条件分支

**2.4 四象限分析（path 计算兜底）**

- `__root__/<rel>` → 项目根 `<rel>`（不变）
- `__subpath__/<rel>` → length == 1 时 `<stacks[0].path>/<rel>`；length == 0 时**理论上 `_common` 不应该出 `__subpath__/`**（设计约束），若真出现按项目根 `<rel>` 处理 + 警告
- 文档加一句："`_common` 不应放 `__subpath__/` 内容；若违反，length=0 项目按 `__root__` 落点 + 输出警告"

**2.5 处理 skipped（读位置切换）**

- 改：length == 1 时读 `stacks[0].skipped`；length == 0 时读 marker 顶层 `skipped`（新字段）
- 顶层 `skipped` schema 与 `stacks[0].skipped` 完全一致，只是位置不同
- 设计权衡：避免引入"虚拟 stack 条目"破坏「`_common` 不进 stacks」约定

**4.2 用户选 stack（加「无 stack」选项）**

- `AskUserQuestion` 选项列表末尾追加一条「无 stack（只 \_common）」
- 选项 description：本项目所有现成 stack 都不合身，仅复用 `_common` 的 stack-无关资源
- 选中后：跳过"选 stack"语义；`stacks` 列表写为 `[]`；其余流程同 4.3，但只扫 `_common/` 一个源

**4.3 全套用模板**

- 已经天然两源并列（`_common` + `<stack>`），length=0 时去掉 `<stack>` 那一个，保留 `_common`
- 显式说明：length=0 项目，`_common` 是唯一来源

**6 节执行（skipped 写回位置）**

- 与 2.5 对称：length == 1 写 `stacks[0].skipped[]`；length == 0 写顶层 `skipped[]`
- 注：6 节中提到的 label sync helper 调用不受影响（它读 `.github/labels.yml`，与 stack 无关）

**6.1 更新 marker**

- length == 1：`template_commit` 更新 + `stacks[0].skipped` 按 6 节策略（原行为，不变）
- length == 0：`template_commit` 更新 + 顶层 `skipped` 按 6 节策略
- Adopt 模式：`bootstrap_time` + `source` 同原逻辑；`stacks` 按用户选择写 `[]` 或 `[{stack, path: ".", skipped: []}]`

### 文件 2：`docs/11-跨项目共享模板与sync-skill/SCHEMA.md`

- **§ 字段定义**：在 yaml 顶层 schema 块加可选 `skipped`（length=0 项目用），注明与 `stacks[0].skipped` 互斥
- **§ `stacks`**：把"本轮（round 11）实现仅支持长度 = 1"改成"本轮支持长度 0 或 1（length=0 = 无 stack 只 \_common；length=1 = 单 stack）；多 stack monorepo 留至后续 round"
- **§ 完整示例**：新增"无 stack 项目（只 \_common）"块，长这样：
  ```yaml
  source: https://github.com/pkulijing/claude-code-global
  template_commit: a1b2c3d4...
  bootstrap_time: 2026-04-27T16:12:55Z
  stacks: [] # 无 stack（只 _common），适用于模板源仓库本身或所有现成 stack 都不合身的项目
  skipped: [] # length=0 项目的 skipped 放顶层（与 stacks[0].skipped 互斥）
  ```
- **§ 关于 `_common` 伪 stack**：补一段「length=0 项目」的描述，明确 `_common` 是该形态项目的唯一模板来源

## 关键修改文件

- `skills/sync-project-config/SKILL.md`（多段，详见上）
- `docs/11-跨项目共享模板与sync-skill/SCHEMA.md`（字段表 + 示例 + `_common` 段补述）

## 不改动的部分

- `_common` 自动应用、不进 `stacks` 列表的约定 → 不变
- `stacks[0].path` 断言（length == 1 分支下保持 = `.`）→ 不变
- marker 顶层 `source` / `template_commit` / `bootstrap_time` 字段语义 → 不变
- helper `platform_issue.py` → 不动（与 stack 无关）

## 验证

本仓库本身就是 dogfood 用例。改完后：

1. 直接在本仓库根跑 `/sync-project-config`，验证：
   - 读到 `stacks: []` 不再报"多 stack / 非根 path"错
   - 正常计算 `_common` 的 diff、列 TODO
   - 用户选 accept/skip 后，skipped 正确写回顶层位置
   - marker `template_commit` 正确更新到 `~/.claude/global-repo` 当前 HEAD
2. 反向兼容验证：找另一个已 bootstrap 的 python-uv 项目（如有）跑一次，验证 `len(stacks) == 1` 路径仍按原行为
3. Adopt 模式验证：在一个全新的非 git 仓库外建临时目录、`git init`、跑 `/sync-project-config`，确认「无 stack（只 \_common）」选项出现且选中后正确写出 `stacks: []` marker

无需写单测（SKILL.md 是给 AI 读的 prose，不是可执行代码；schema 改动靠 dogfood 验证）。
