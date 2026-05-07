---
name: sync-project-config
description: 把 claude-code-global 仓库管理的"跨项目共享开发配置模板"的最新变化同步进当前项目；含 adopt 模式（无 marker 老项目首次接入）
disable-model-invocation: false
---

用户调用此 skill 表示要把仓库的模板（`~/.claude/templates/<stack>/`）变化反映到当前项目。两种模式：

- **Normal sync**：项目根已有 `.cc-template.yml` marker → 计算 diff → AI 智能 merge 提议 → 用户批量决策 → 执行
- **Adopt**：无 marker → 让用户选 stack → 当作"全是新增"完整套用一次（含冲突询问）→ 写 marker

详细 schema：`~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/SCHEMA.md`
设计与决策：`~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/PROMPT.md` / `PLAN.md`

## 前置检查

按顺序，**任一失败立即停止并报告原因**：

- 当前目录必须是 git 仓库：`git rev-parse --is-inside-work-tree` 返回 true
- `~/.claude/templates/` 必须存在且至少含一个 stack 子目录
- `~/.claude/global-repo/` 必须存在且为指向本仓库的软链
- `~/.claude/global-repo/` 内必须能跑 `git rev-parse HEAD`（即仓库未损坏）

任一失败 → 提示用户重跑 `bash ~/.claude/global-repo/install.sh` 并退出。

## 模式判断

读项目根 `.cc-template.yml`：

- **不存在** → 进入第 4 节「Adopt 模式」
- **存在** → 进入第 2 节「Normal sync」

## 2. Normal sync：解析 marker + 计算变更

### 2.1 解析 marker

直接 Read 文件、按 YAML 语义读字段。需要：

- `template_commit`（旧 commit hash）
- `stacks[0].stack`、`stacks[0].path`、`stacks[0].skipped`（数组）

**断言**（本轮仅支持单 stack）：

- `stacks` 列表 length 必须等于 1
- `stacks[0].path` 必须等于 `.`
- 任一不满足 → 报错「检测到多 stack / 非根 path 配置，本轮不支持，留至后续 round」并退出

### 2.2 拿当前模板 HEAD

```bash
NEW_COMMIT=$(git -C ~/.claude/global-repo rev-parse HEAD)
```

如果 working copy 有未提交修改：

```bash
git -C ~/.claude/global-repo status --porcelain templates/
```

非空 → 警告用户「`~/.claude/global-repo` 的 templates 有未提交修改，sync 仅基于 HEAD 进行，未提交内容不会同步」。

### 2.3 计算模板变更

**两个源都要扫**：用户选定的 `<stack>/` + 自动应用的 `_common/`（如果 `~/.claude/templates/_common/` 存在）：

```bash
git -C ~/.claude/global-repo diff --name-status <old>..<new> -- templates/<stack>/ templates/_common/
```

输出形如：

- `M templates/python-uv/__root__/.gitignore`（修改，来源 stack）
- `A templates/_common/__root__/.github/ISSUE_TEMPLATE/feat.md`（新增，来源 \_common）
- `D templates/python-uv/__subpath__/.vscode/old.json`（删除）

若输出为空 → 报告「模板自上次同步起未变化」，再继续走 skipped 重检（2.5）。

### 2.4 对每个变更文件做四象限分析

对应到项目侧路径：

- `__root__/<rel>` → 项目根的 `<rel>`
- `__subpath__/<rel>` → `<path>/<rel>`（单 stack 项目 path = `.`）

来源（stack 或 \_common）只影响模板侧路径，**项目侧落点完全相同** —— 因此 stack 与 \_common **不应有同名冲突**（设计约束）；万一有，stack 优先。

读取 3 份内容做对比（`<source>` 是 `<stack>` 或 `_common`）：

- 模板旧版：`git -C ~/.claude/global-repo show <old>:templates/<source>/<scope>/<rel>`
- 模板新版：直接读 `~/.claude/templates/<source>/<scope>/<rel>`
- 项目侧现状：直接 Read 项目侧路径

四象限：

| 模板侧 | 项目侧                     | 默认建议                                         |
| ------ | -------------------------- | ------------------------------------------------ |
| 修改   | 与旧模板一致（未自定义）   | take 新模板（clean update）                      |
| 修改   | 与旧模板不一致（已自定义） | AI 智能 merge：保留用户修改语义 + 引入模板新内容 |
| 新增   | 不存在                     | 创建                                             |
| 新增   | 已存在（罕见）             | 询问 take / 保留 / 智能 merge                    |
| 删除   | 仍存在                     | 询问删除 / 保留（用户可能仍需要）                |

特殊：`pyproject.toml.ruff.fragment` 永远不直接写文件，做项目根 `pyproject.toml` 的 `[tool.ruff]` 段合并；项目无 pyproject.toml → 标记此文件「skipped: 项目无 pyproject.toml」。

### 2.5 处理 skipped 持久化语义

对 marker 中 `stacks[0].skipped` 每条：

- 取 `file`（含来源 source 段，如 `__root__/.github/labels.yml`） 与 `skipped_at_commit`
- 该文件实际来源（stack 或 \_common）由 skill 在分析阶段记录到 file 字段或动态确定
- 跑 `git -C ~/.claude/global-repo log --oneline <skipped_at_commit>..<new> -- templates/<source>/<file>`（`<source>` 是该文件实际来源 stack 或 \_common）
- 输出**为空**（该文件自 skip 之后未变） → **自动跳过、不进 TODO**
- 输出**非空**（变了） → **重新进 TODO**，标注「上次 skip 在 commit X，之后又改过」

### 2.6 输出 TODO 清单

格式（每文件一项）：

```
TODO 同步清单（共 N 项）：

[1] .gitignore （root）
    模板侧动作：M（modified）
    模板变化摘要：新增 .ruff_cache/
    项目侧状态：用户已自定义（手动加过 *.bak）
    建议：智能 merge — 保留 *.bak、追加 .ruff_cache/

[2] .github/workflows/lint.yml （root）
    模板侧动作：A（added）
    项目侧状态：不存在
    建议：创建

...
```

跳到第 5 节「用户批量决策」。

## 3. Normal sync 无变化退出条件

如果 2.3 输出空 + 2.5 没有"被重新提案的 skipped 项" + 没有需新增/删除的文件 → 报告「无需同步，模板与项目已对齐」并退出，不写 marker。

## 4. Adopt 模式（无 marker）

### 4.1 探测可用 stack

`~/.claude/templates/` 下非下划线开头的子目录列表。

### 4.2 用户选 stack

用 `AskUserQuestion`：列出可选 stack，让用户选一个。本轮单 stack only，path 固定 `.`，不询问 path。

### 4.3 全套用模板（含冲突询问）

把以下两个源的 `__root__/*` + `__subpath__/*` 全部当作"待新增"列入 TODO：

- `~/.claude/templates/_common/`（如存在，**自动应用**）
- `~/.claude/templates/<stack>/`（用户选定）

判断：

- 项目侧不存在 → 默认建议「创建」
- 项目侧已存在 → AI 对比模板内容与项目内容：
  - 完全一致 → 默认建议「无需操作（已等价）」
  - 不一致 → 默认建议「智能 merge」或询问 take / 保留 / merge
- `pyproject.toml.ruff.fragment` 同 2.4 特殊处理
- 含 `.github/labels.yml` 时：**额外把"调 `gh label create` 同步到 GitHub"作为单独一条 TODO**。是否真正下发由 `git remote get-url origin` 判定（详见第 6 节执行步骤）：origin 含 `github.com` → 走 GitHub 同步；origin 含 `gitlab` 字样 → 该条标 skipped 并提示「检测到 GitLab remote，labels 同步留待后续 `gh→glab` 适配 issue」；其他（无 origin / 自托管 GitLab 等）→ 该条标 skipped 并提示「无法从 origin 判定平台，labels 同步跳过」

跳到第 5 节。

## 5. 用户批量决策

向用户呈现 2.6 / 4.3 的 TODO，让用户给出**统一指令**，例如：

> 「全部 accept；第 3 条 skip；第 5 条改成全替模板，不要 merge」

AI 解析指令、产出最终执行计划，再次回显（per-file 写出每条最终动作）让用户**显式确认**后才执行。

## 6. 执行

按确认后的计划逐条执行：

- **accept (新增)**：写文件
- **accept (修改/智能 merge)**：用 Edit / Write 写回合并后内容
- **accept (删除)**：删文件
- **accept (pyproject 段合并)**：把 fragment 合并进 `pyproject.toml [tool.ruff]` 段
- **accept (gh label sync)**：先按 origin URL 判定平台再决定动作：
  - `git remote get-url origin` 含 `github.com` → 解析 `.github/labels.yml`，对每条调 `gh label create --force "<name>" --color "<color>" --description "<desc>"`（`gh auth` 失败则降级为提示，不阻塞）
  - origin 含 `gitlab` 字样（含自托管时含 `gitlab` 字样的 URL）→ **跳过**，打印「检测到 GitLab remote，labels 同步将在后续 `gh→glab` 适配 issue 落地，本轮请手动维护或暂缓」
  - 其他（无 origin / 自托管 GitLab URL 不含 `gitlab` 字样 / 等）→ **跳过**，打印「无法从 origin 判定平台，labels 同步跳过；如确为 GitHub 请补 origin remote 后重跑 sync，如为 GitLab 暂留待后续 issue 落地」
  - 本轮**不**调 `glab label create`（GitLab labels 同步整体留给后续 issue）
- **skip**：在 marker 的 `stacks[0].skipped[]` 中追加 / 更新条目，字段：`file`、`skipped_at_commit: <NEW_COMMIT>`、`reason: <可选，让用户填或留空>`

注意：skipped[] 的更新策略：

- 已在 skipped[] 中且本次仍 skip → 更新 `skipped_at_commit` 为 `NEW_COMMIT`
- 已在 skipped[] 中但本次 accept（即用户改主意了）→ 从 skipped[] 移除
- 不在 skipped[] 中且本次新 skip → 追加新条目

### 6.1 更新 marker

回写 `.cc-template.yml`：

- `template_commit` 更新为 `NEW_COMMIT`
- `bootstrap_time` 不动（这是首次 bootstrap 时间）
- `source` 不动
- `stacks[0].skipped` 按 6 节策略更新

Adopt 模式额外：

- `bootstrap_time` 设为当前 ISO 时间
- `source` 取 `git -C ~/.claude/global-repo config --get remote.origin.url`，无则填占位

### 6.2 收尾反馈

列出实际改动的项目侧文件清单（path-by-path），提示用户：

1. `git diff` 自行 review
2. 如需启用 pre-commit：`pre-commit install` 后 `pre-commit run --all-files` 验证
3. 满意后用 `/commit` 或自行 `git commit`

**不自动 commit** —— 由用户决策（与 `/bootstrap`、`/backlog` 一致）。
