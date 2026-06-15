---
name: sync-project-config
description: 把 claude-code-global 仓库管理的"跨项目共享开发配置模板"的最新变化同步进当前项目；含 adopt 模式（无 marker 老项目首次接入）
disable-model-invocation: false
---

用户调用此 skill 表示要把仓库的模板（`~/.claude/templates/<stack>/`）变化反映到当前项目。两种模式：

- **Normal sync**：项目根已有 `.agent-template.yml` marker → 计算 diff → AI 智能 merge 提议 → 用户批量决策 → 执行
- **Adopt**：无 marker → 让用户选 stack（或选"无 stack 只 \_common"） → 当作"全是新增"完整套用一次（含冲突询问）→ 写 marker

**两种项目形态**（本轮均支持）：

- **单 stack 项目（`len(stacks) == 1`）**：选定某个 stack（如 `python-uv`），`<stack>` + `_common` 两个模板源都参与
- **无 stack 项目（`len(stacks) == 0`）**：仅 `_common` 一个源参与，适用于模板源仓库本身（`claude-code-global`）或所有现成 stack 都不合身、但仍想复用 `_common` stack-无关资源（issue templates、`labels.yml`、`.prettierrc` 等）的项目

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

### 旧名 marker 自动迁移

marker 文件名在 round 22 由 `.cc-template.yml` 改为 `.agent-template.yml`。读 marker 前先做一次迁移检查：

- 项目根存在旧名 `.cc-template.yml` 且**不存在**新名 `.agent-template.yml` → 用 `git mv .cc-template.yml .agent-template.yml` 重命名（前置检查已确保是 git 仓库），并明确告知用户「检测到旧版 marker 文件名，已自动迁移为 `.agent-template.yml`」。
- 两者**同时存在** → 报冲突并停止，请用户手动处理（不猜测哪个为准）。
- 其余情况不动。

### 判断模式

读项目根 `.agent-template.yml`：

- **不存在** → 进入第 4 节「Adopt 模式」
- **存在** → 进入第 2 节「Normal sync」

## 2. Normal sync：解析 marker + 计算变更

### 2.1 解析 marker

直接 Read 文件、按 YAML 语义读字段。需要：

- `template_commit`（旧 commit hash）
- `stacks` 列表
- length == 1 时再读 `stacks[0].stack`、`stacks[0].path`、`stacks[0].skipped`（数组）
- length == 0 时改读 marker **顶层** `skipped`（数组，可缺省视作空数组）

**断言**（本轮支持 length 0 或 1）：

- `stacks` 列表 length 必须 ≤ 1
- length == 1 时 `stacks[0].path` 必须等于 `.`
- 任一不满足 → 报错「检测到多 stack / 非根 path 配置，本轮不支持，留至后续 round」并退出

后续 2.x / 6.x 中所有「`<stack>`」「`stacks[0].*`」描述都只在 length == 1 时适用；length == 0 时按"仅 `_common`"分支走，具体每节会显式说明。

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

**扫的模板源由 `stacks` 长度决定**：

- **length == 1**：用户选定的 `<stack>/` + 自动应用的 `_common/`

  ```bash
  git -C ~/.claude/global-repo diff --name-status <old>..<new> -- templates/<stack>/ templates/_common/
  ```

- **length == 0**：仅 `_common/`

  ```bash
  git -C ~/.claude/global-repo diff --name-status <old>..<new> -- templates/_common/
  ```

  ⚠️ 不要省略 pathspec：`git diff` 不传路径会扫全 templates、误把其他 stack 的变更带进来。

输出形如：

- `M templates/python-uv/__root__/.gitignore`（修改，来源 stack）
- `A templates/_common/__root__/.github/ISSUE_TEMPLATE/feat.md`（新增，来源 \_common）
- `D templates/python-uv/__subpath__/.vscode/old.json`（删除）

若输出为空 → 报告「模板自上次同步起未变化」，再继续走 skipped 重检（2.5）。

### 2.4 对每个变更文件做四象限分析

对应到项目侧路径：

- `__root__/<rel>` → 项目根的 `<rel>`
- `__subpath__/<rel>` → length == 1 时 `<stacks[0].path>/<rel>`（单 stack 项目 path 恒为 `.`，等同项目根）
- length == 0 时**理论上 `_common` 不应该出 `__subpath__/` 内容**（设计约束：`_common` 只承载 stack-无关、根级资源）；若违反，按项目根 `<rel>` 兜底 + 输出警告

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

特殊：`pyproject.toml.*.fragment` 永远不直接写文件，做项目根 `pyproject.toml` 的对应段合并。

- 命名约定：`pyproject.toml.<section>.fragment`，`<section>` 用 `-` 分隔层级（如 `ruff` → `[tool.ruff]`、`uv` → `[tool.uv]`、`uv-index` → `[[tool.uv.index]]`）。
- 合并语义：项目侧无此段 → 直接追加；已有此段 → AI 智能合并，保留用户自定义字段，模板新增字段追加；冲突字段询问用户。
- 数组段（双方括号，如 `[[tool.uv.index]]`）：按 `name` 字段 union（项目侧已有同名条目则跳过，避免重复注册）。
- 项目无 `pyproject.toml`：
  - normal sync 路径 → 标记「skipped: 项目无 pyproject.toml」
  - adopt 路径下选了 `python-uv` stack → 标记为「待 4.4 完成 `uv init` 后合并」
  - 其他情况仍按 skipped 处理

### 2.5 处理 skipped 持久化语义

**skipped 列表的读取位置随 `stacks` 长度切换**：

- **length == 1**：读 `stacks[0].skipped`
- **length == 0**：读 marker **顶层** `skipped`（与 `stacks[0].skipped` schema 完全一致，仅位置不同；该字段可缺省，视作空数组）

  这样设计是为了避免在 length=0 时引入"虚拟 stack 条目"破坏既有「`_common` 不显式记录在 `stacks` 列表」约定。

对选定列表的每条：

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

询问用户：列出可选 stack，让其选一个。本轮 path 固定 `.`，不询问 path。

**选项列表末尾追加一条「无 stack（只 \_common）」**：

- label：`无 stack（只 _common）`
- description：本项目所有现成 stack 都不合身，仅复用 `_common` 的 stack-无关资源（issue templates、`labels.yml`、`.prettierrc` 等）。适用于模板源仓库本身（`claude-code-global`）或确认所有 stack 都不合身的项目。

用户选中此项时：跳过"选 stack"语义；4.3 仅扫 `_common/` 一个源；marker 中 `stacks` 字段最终写为 `[]`。

### 4.3 全套用模板（含冲突询问）

**待新增的模板源由 4.2 选择决定**：

- 选了具体 stack：以下两个源的 `__root__/*` + `__subpath__/*` 全部当作"待新增"列入 TODO
  - `~/.claude/templates/_common/`（如存在，**自动应用**）
  - `~/.claude/templates/<stack>/`（用户选定）
- 选了「无 stack（只 \_common）」：仅 `~/.claude/templates/_common/` 一个源

判断：

- 项目侧不存在 → 默认建议「创建」
- 项目侧已存在 → AI 对比模板内容与项目内容：
  - 完全一致 → 默认建议「无需操作（已等价）」
  - 不一致 → 默认建议「智能 merge」或询问 take / 保留 / merge
- `pyproject.toml.*.fragment` 同 2.4 特殊处理
- 含 `.github/labels.yml` 时：**额外把"调 helper `label-sync-from-file` 同步 labels 到远端"作为单独一条 TODO**。helper 自动按 `git remote` 判定走 `gh` / `glab`（详见第 6 节执行步骤）。`.github/labels.yml` schema 跨平台一致，GitLab 项目下也读 `.github/` 路径同一份（不新建 `.gitlab/labels.yml` 副本）。

跳到第 5 节。

### 4.4 （仅 python-uv stack）项目实际可跑化

stack ≠ `python-uv` 则**整段跳过**。stack == `python-uv` 时，**先询问用户确认是否执行**（默认 yes，给「只要配置不要装依赖」选项），yes 则按以下子步骤逐条执行；no 则跳过整段并把决策记录到收尾反馈。

逻辑等同 bootstrap 的 Step 3.5，区别在 adopt 模式下 `pyproject.toml` **更可能已存在**（老项目），4.4.1 跳过 `uv init` 是常态。

#### 4.4.1 确保 pyproject.toml 存在

```bash
[ -f pyproject.toml ] && echo "exists, skip uv init" || uv init --package
```

`--package` 让 uv 直接落标准 src 布局（生成 `src/<pkg>/__init__.py` 空文件 + 含 `[build-system] uv_build` 的 `pyproject.toml`），由领域规则 `~/.claude/rules/python.md` §2 固化。adopt 模式下 `pyproject.toml` 多半已存在，本步是 no-op；空目录走 `uv init --package` 分支。

跑完后回处理 2.4 标记「待 4.4 后合并」的所有 `pyproject.toml.*.fragment`（清华源段必须先合，否则 4.4.2 在国内会卡）。

#### 4.4.2 装常用 dev 依赖

```bash
uv add --dev pytest pytest-cov ruff
```

uv 会跳过已装的，幂等。失败 → 报告 stdout/stderr，提示用户手动重试 + 暂停 skill，**不**自动回滚已写文件。

#### 4.4.3 确保 pre-commit 全局可用

```bash
command -v pre-commit >/dev/null || uv tool install pre-commit
```

#### 4.4.4 注册 git hook

```bash
pre-commit install
```

成功后打印 `pre-commit installed at .git/hooks/pre-commit`。**不**强制跑 `pre-commit run --all-files`（首次接入易出大量 finding，让用户自决）。

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
- **accept (pyproject 段合并)**：把 `pyproject.toml.<section>.fragment` 合并进 `pyproject.toml` 的对应段（按 2.4 命名约定与合并语义）
- **accept (label sync)**：调 helper 自动按平台 dispatch：

  ```bash
  python3 $HOME/.claude/scripts/platform_issue.py label-sync-from-file .github/labels.yml
  ```

  - GitHub → 内部对每条 yml 调 `gh label create --force ...`（`--force` 在已存在时覆盖更新）
  - GitLab → 内部先 `glab label list --output json` 拿现存 name→id 映射，存在则 `glab label edit -l <id> -c #<hex> -d <desc>`，否则 `glab label create -n <name> -c #<hex> -d <desc>`；color 自动加 `#` 前缀
  - helper exit 2（unknown 平台 / 无 origin / 自托管 URL 不含 `gitlab` 字样）→ 降级为提示「labels 同步跳过；如确为 GitHub 请补 origin remote，如确为自托管 GitLab 加 `--platform gitlab` override 重跑」
  - helper exit 3（auth 失败）→ 降级为提示「跑 `gh auth login` 或 `glab auth login` 后重试」，不阻塞其他 accept 项
  - helper exit 4（CLI 缺失）→ 降级为提示「先 `brew install gh` / `brew install glab`」
  - stdout 输出每条 label 的 TSV 同步结果与 summary，原样展示给用户

- **skip**：在 marker 的 skipped 列表中追加 / 更新条目，字段：`file`、`skipped_at_commit: <NEW_COMMIT>`、`reason: <可选，让用户填或留空>`
  - length == 1 项目：写 `stacks[0].skipped[]`
  - length == 0 项目：写 marker 顶层 `skipped[]`（与 2.5 读取位置对称）

注意：skipped[] 的更新策略：

- 已在 skipped[] 中且本次仍 skip → 更新 `skipped_at_commit` 为 `NEW_COMMIT`
- 已在 skipped[] 中但本次 accept（即用户改主意了）→ 从 skipped[] 移除
- 不在 skipped[] 中且本次新 skip → 追加新条目

### 6.1 更新 marker

回写 `.agent-template.yml`：

- `template_commit` 更新为 `NEW_COMMIT`
- `bootstrap_time` 不动（这是首次 bootstrap 时间）
- `source` 不动
- skipped 按 6 节策略更新：
  - length == 1：`stacks[0].skipped`
  - length == 0：marker 顶层 `skipped`

Adopt 模式额外：

- `bootstrap_time` 设为当前 ISO 时间
- `source` 取 `git -C ~/.claude/global-repo config --get remote.origin.url`，无则填占位
- `stacks` 按 4.2 用户选择写：
  - 选了具体 stack → `[{stack: <name>, path: ".", skipped: []}]`
  - 选了「无 stack（只 \_common）」→ `[]`，同时顶层加 `skipped: []`

### 6.2 收尾反馈

列出实际改动的项目侧文件清单（path-by-path），提示用户：

1. `git diff` 自行 review
2. 如新加入的 `.pre-commit-config.yaml` 还未生效，跑 `pre-commit install`（adopt 模式 4.4 已自动做过；normal sync 不做）；可选跑 `pre-commit run --all-files` 验证
3. 满意后用 `/commit` 或自行 `git commit`

**不自动 commit** —— 由用户决策（与 `/bootstrap`、`/backlog` 一致）。
