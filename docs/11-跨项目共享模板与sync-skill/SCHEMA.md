# `.cc-template.yml` Schema

`.cc-template.yml` 是项目侧的 marker 文件，告诉 `/sync-project-config` 这个项目接入了哪个 stack 的模板、上次同步到哪个 commit、有哪些条目用户主动 skip 过。

**位置**：项目根目录
**应当 commit 进 git**（让团队和 CI 都看到）
**编码**：UTF-8 / YAML 1.2

## 字段定义

```yaml
# （顶部注释，提示 marker 由 claude-code-global 管理）
source: <string, URL>
template_commit: <string, git commit hash>
bootstrap_time: <string, ISO 8601 timestamp>
stacks:
  - stack: <string, stack 名>
    path: <string, 相对路径，单 stack 项目固定为 ".">
    skipped:
      - file: <string, 模板内的相对路径，含 scope 后部分>
        skipped_at_commit: <string, 当时模板 commit>
        reason: <string, 可选，用户填>
# 仅 length == 0（无 stack 项目）使用，与 stacks[0].skipped 互斥
skipped:
  - file: <string>
    skipped_at_commit: <string>
    reason: <string, 可选>
```

### `source`（必填）

模板仓库的 URL，通常是 `claude-code-global` 仓库的 GitHub origin。

- bootstrap 时由 skill 通过 `git -C ~/.claude/global-repo config --get remote.origin.url` 自动取值
- 取不到（仓库无 origin）时填占位符 `https://github.com/<owner>/claude-code-global`，并提示用户手工补全
- 未来支持多 fork / 多源时，sync skill 会用此字段验证"我从哪个仓库来"

### `template_commit`（必填）

最后一次成功 sync 时模板仓库的 commit hash。`/sync-project-config` 启动时拿当前 HEAD 与此值做 `git diff <template_commit>..HEAD -- templates/<stack>/`，得出本次需要 propagate 的变化。

每次 sync 成功执行（写入文件）后由 skill 更新为新 HEAD。

### `bootstrap_time`（必填）

首次 bootstrap 或 adopt 完成的 ISO 8601 timestamp（UTC）。**纯信息字段**，sync 不会改它。便于追溯项目接入模板的时间。

### `stacks`（必填，列表）

项目使用的 stack 列表。**支持长度 0、1 或多条**（length=1 起于 round 11，length=0 放宽于 round 18，多 stack 叠加放宽于 round 30）：

- **length == 0**（无 stack 项目，只 `_common`）：本仓库 `claude-code-global` 自身，或所有现成 stack 都不合身、但仍想复用 `_common` stack-无关资源的项目
- **length == 1**（单 stack 项目）：选定某个 stack（如 `python-uv`），`<stack>` + `_common` 两个模板源都参与
- **length >= 2**（多 stack 项目）：前端 / 后端正交叠加（如 `python-uv` 落根 + `react-vite` 落 `frontend/`），各 stack 按各自 `path` 落点 + `_common` 一并参与

各 stack 的 `path` 由其 `templates/<stack>/stack.yml` 的 `default_path` 决定（`python-uv` 无 `stack.yml` → `.`、`react-vite` → `frontend`），bootstrap / adopt 写入 marker，**不**向用户交互询问。本轮**不**做交互式自定义 path、也**不**做 monorepo 根级同名文件（如前后端各自 `.gitignore`）的精细冲突合并 —— 留至后续 round。

### `skipped`（可选，顶层，仅 length == 0 使用）

无 stack 项目（`stacks: []`）的 skipped 条目放在 marker 顶层（不能塞进 `stacks[0]`，因为没有 `stacks[0]`）。schema 与 `stacks[].skipped` 完全一致。

- length == 0 时：sync 读写顶层 `skipped`，`stacks[0].skipped` 不存在
- length == 1 时：sync 读写 `stacks[0].skipped`，顶层 `skipped` 不应出现（若出现 → 忽略 + 警告）

#### `stacks[].stack`（必填）

stack 名称，对应 `~/.claude/templates/<stack>/` 目录。如 `python-uv`、`node`（未来）。

#### `stacks[].path`（必填）

stack 应用到的项目子路径（相对项目根），取自该 stack 的 `stack.yml` `default_path`。

- 后端 `python-uv`：`.`（落仓库根，维持历史、与现有单 stack 项目兼容）
- 前端 `react-vite`：`frontend`（落子目录，与后端正交、可同仓并存）
- 缺省（stack 无 `stack.yml` 或未写 `default_path`）：`.`

#### `stacks[].skipped`（必填，可空数组）

用户在 sync TODO 中主动 skip 的条目。`/sync-project-config` 用它实现"持久化跳过 + 模板再变就重新提案"语义。

##### `skipped[].file`（必填）

模板内的相对路径，含 scope 子目录但不含 `templates/<stack>/` 前缀。例如：

- `__root__/.gitignore`
- `__subpath__/biome.json`
- `__root__/.vscode/settings.json.fragment`（fragment 类，见文末「与文件 scope 的关系」）

##### `skipped[].skipped_at_commit`（必填）

用户做出 skip 决策时的模板 commit hash。下一次 sync 时：

- `git log <skipped_at_commit>..HEAD -- templates/<stack>/<file>` 输出**为空**（该文件之后未变）→ 自动跳过、不再提案
- 输出**非空**（变了）→ 重新进 TODO 让用户重新决策（标注「上次 skip 在 commit X」）

##### `skipped[].reason`（可选）

用户填的 skip 原因，纯文本。便于半年后回看时理解。可空可省。

## 完整示例

### 单 stack 项目（最常见形态）

```yaml
# 由 claude-code-global 管理，非必要请勿手动编辑
source: https://github.com/pkuyplijing/claude-code-global
template_commit: a1b2c3d4e5f6789012345678901234567890abcd
bootstrap_time: 2026-04-27T14:30:00Z
stacks:
  - stack: python-uv
    path: .
    skipped:
      - file: __root__/.github/workflows/lint.yml
        skipped_at_commit: a1b2c3d4e5f6789012345678901234567890abcd
        reason: 项目用 Jenkins 不用 GitHub Actions
```

### 无 stack 项目（只 `_common`，round 18 引入）

```yaml
# 由 claude-code-global 管理，非必要请勿手动编辑
source: https://github.com/pkulijing/claude-code-global
template_commit: ecbb9d4b4e03aa93bc716384cc3141464ee4af04
bootstrap_time: 2026-04-27T16:12:55Z
stacks: [] # 无 stack：仅 _common 自动应用
skipped: [] # 顶层 skipped（与 stacks[0].skipped 互斥）
```

适用场景：

- 模板源仓库本身（如 `claude-code-global`）—— stack 模板再设计也轮不到自己用
- 所有现成 stack 都不合身的项目（如纯 bash + jq 工具仓库），仍想复用 `_common` 的 stack-无关资源（issue templates、`labels.yml`、`.prettierrc`）

### 多 stack 项目（前端 + 后端并存，round 30 起 bootstrap / sync 支持）

后端落仓库根、前端落 `frontend/` 子目录，正交叠加：

```yaml
source: https://github.com/pkuyplijing/claude-code-global
template_commit: a1b2c3d4e5f6789012345678901234567890abcd
bootstrap_time: 2026-04-27T14:30:00Z
stacks:
  - stack: python-uv
    path: .
    skipped: []
  - stack: react-vite
    path: frontend
    skipped: []
```

## 与文件 scope 的关系

模板里每个文件归属一个 scope：

- `__root__/<rel>` → 写到 git 仓库根的 `<rel>`（任何 stack 与 `_common` 都落根）
- `__subpath__/<rel>` → 写到该文件来源 stack 的 `<path>/<rel>`

`python-uv`（path `.`）两种 scope 都落项目根；`react-vite`（path `frontend`）的 `__subpath__` 落 `frontend/`。前后端并存时各 stack 的 `__subpath__` 落各自子树、天然不撞；`__root__` 由各 stack 与 `_common` 共同贡献到根（不应有同名冲突，万一有 stack 优先）。

### fragment 文件（不直接落地，合并进目标）

例外：文件名以 `.fragment` 结尾的不按上表 verbatim 落地，而是去掉 `.fragment` 后缀得目标相对路径（始终落**项目根**），由 bootstrap / sync **合并**进目标。当前两类：

- `pyproject.toml.<section>.fragment` → 根 `pyproject.toml` 对应段（TOML 段合并；`<section>` 用 `-` 分隔层级，如 `uv-index` → `[[tool.uv.index]]`）。
- `.vscode/<name>.json.fragment` → 根 `.vscode/<name>.json`（JSON 合并：`recommendations` 数组 union / `settings.json` 顶层键 union）。round 32 引入，把各 stack 的编辑器配置统一汇聚到项目根 `.vscode/`（含子目录 stack `react-vite`），解决「VS Code 单根工作区只读仓库根 `.vscode/`、子目录配置不生效」。

因此 fragment 让「`__root__` 不应同名冲突」的约束对编辑器配置成立：多个 stack 各出一份 `.vscode/<name>.json.fragment`，合并而非覆盖。

## 关于 `_common` 伪 stack（round 12 引入）

`~/.claude/templates/_common/` 是承载完全 stack-无关的根级资源（如 issue templates、`.prettierrc`、`.github/labels.yml`）的"伪 stack"。

- bootstrap / sync **自动应用** \_common，**不**在 marker 的 `stacks` 列表中显式记录
- 用户在 bootstrap / sync 选 stack 时，下划线开头的目录被过滤，`_common` 不出现在选项里（但 adopt 选 stack 时**额外**会出现一条「无 stack（只 \_common）」选项 —— 选中后 `stacks` 写空数组，仍只走 \_common 这一个隐式源）
- \_common 与 stack 不应有同名冲突；万一有，stack 优先
- \_common 只承载 `__root__/` 内容；不应放 `__subpath__/` 内容（无 stack 项目下没有有效 path 落点）

由此 `stacks` 列表只反映"用户选定的应用 stack"，\_common 始终是约定的隐式行为：

- length == 1 项目：\_common 与 `<stack>` 一起参与
- length == 0 项目（round 18 引入）：\_common 是**唯一**模板来源

## 关于平台双兼容（round 14 引入）

`_common` 与各 stack 的模板内容**同时**包含 GitHub 与 GitLab 两个平台的等价物，由 bootstrap / sync 一起复制到目标项目，不按当前 remote 过滤：

| 平台   | 文件                                          | 来源模板    |
| ------ | --------------------------------------------- | ----------- |
| GitHub | `.github/ISSUE_TEMPLATE/{feat,bug,spike}.md`  | `_common`   |
| GitHub | `.github/labels.yml`                          | `_common`   |
| GitHub | `.github/workflows/lint.yml`                  | `python-uv` |
| GitLab | `.gitlab/issue_templates/{feat,bug,spike}.md` | `_common`   |
| GitLab | `.gitlab-ci.yml`                              | `python-uv` |

**互不干扰前提**：

- GitHub Actions 只读 `.github/workflows/`、不看 `.gitlab-ci.yml`
- GitLab CI 只读 `.gitlab-ci.yml`、不看 `.github/workflows/`
- GitHub Issues 只读 `.github/ISSUE_TEMPLATE/`、GitLab Issues 只读 `.gitlab/issue_templates/`
- 因此对端文件在另一平台等同于死文件，零意外行为

`.cc-template.yml` 不增加 `platform` 字段；marker schema 不变。

skill 中真正调命令行的步骤（如 `gh label create`）按 `git remote get-url origin` 的输出动态判定：

- origin 含 `github.com` → 走 `gh` 分支
- origin 含 `gitlab` 字样 → 当前**跳过**（本轮不实现 `glab` 调用）
- 其他（无 origin / 自托管 GitLab URL 不含 `gitlab` 字样 / 等）→ 跳过 + 提示

后续会有独立 issue 跟踪 skill 内 `gh issue *` / `gh label *` 等所有 `gh` 调用的双轨适配（含 GitLab labels 同步）。
