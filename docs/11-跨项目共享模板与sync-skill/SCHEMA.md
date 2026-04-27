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

项目使用的 stack 列表。**本轮（round 11）实现仅支持长度 = 1**；schema 已为多 stack monorepo 设计，但 `/sync-project-config` 启动时会断言长度 = 1 + `path == "."`，否则报错退出。多 stack 支持留至后续 round。

#### `stacks[].stack`（必填）

stack 名称，对应 `~/.claude/templates/<stack>/` 目录。如 `python-uv`、`node`（未来）。

#### `stacks[].path`（必填）

stack 应用到的项目子路径（相对项目根）。

- 单 stack 项目恒为 `.`
- 多 stack 项目（未来）：例如 `frontend`、`backend`

#### `stacks[].skipped`（必填，可空数组）

用户在 sync TODO 中主动 skip 的条目。`/sync-project-config` 用它实现"持久化跳过 + 模板再变就重新提案"语义。

##### `skipped[].file`（必填）

模板内的相对路径，含 scope 子目录但不含 `templates/<stack>/` 前缀。例如：
- `__root__/.gitignore`
- `__subpath__/.vscode/settings.json`

##### `skipped[].skipped_at_commit`（必填）

用户做出 skip 决策时的模板 commit hash。下一次 sync 时：
- `git log <skipped_at_commit>..HEAD -- templates/<stack>/<file>` 输出**为空**（该文件之后未变）→ 自动跳过、不再提案
- 输出**非空**（变了）→ 重新进 TODO 让用户重新决策（标注「上次 skip 在 commit X」）

##### `skipped[].reason`（可选）

用户填的 skip 原因，纯文本。便于半年后回看时理解。可空可省。

## 完整示例

### 单 stack 项目（本轮支持的形态）

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

### 多 stack monorepo（schema 已支持，本轮 sync 不实现）

```yaml
source: https://github.com/pkuyplijing/claude-code-global
template_commit: a1b2c3d4e5f6789012345678901234567890abcd
bootstrap_time: 2026-04-27T14:30:00Z
stacks:
  - stack: python-uv
    path: backend
    skipped: []
  - stack: react
    path: frontend
    skipped: []
```

## 与文件 scope 的关系

模板里每个文件归属一个 scope：

- `__root__/<rel>` → 写到 git 仓库根的 `<rel>`
- `__subpath__/<rel>` → 写到 `<stacks[].path>/<rel>`

单 stack 项目 `path = .` 时，两种 scope 都落到项目根；语义差异在多 stack 时显现（多 stack 多 stack 共同贡献到 root，AI 跨 stack merge）。

## 关于 `_common` 伪 stack（round 12 引入）

`~/.claude/templates/_common/` 是承载完全 stack-无关的根级资源（如 issue templates、`.prettierrc`、`.github/labels.yml`）的"伪 stack"。

- bootstrap / sync **自动应用** _common，**不**在 marker 的 `stacks` 列表中显式记录
- 用户在 bootstrap / sync 选 stack 时，下划线开头的目录被过滤，`_common` 不出现在选项里
- _common 与 stack 不应有同名冲突；万一有，stack 优先

由此 `stacks` 列表只反映"用户选定的应用 stack"，_common 是约定的隐式行为。
