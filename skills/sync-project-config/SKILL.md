---
name: sync-project-config
description: 把 claude-code-global 仓库管理的"跨项目共享开发配置模板"的最新变化同步进当前项目；含 adopt 模式（无 marker 老项目首次接入）
disable-model-invocation: false
---

用户调用此 skill 表示要把仓库的模板（`~/.claude/templates/<stack>/`）变化反映到当前项目。两种模式：

- **Normal sync**：项目根已有 `.agent-template.yml` marker → 计算 diff → AI 智能 merge 提议 → 用户批量决策 → 执行
- **Adopt**：无 marker → 让用户选 stack（或选"无 stack 只 \_common"） → 当作"全是新增"完整套用一次（含冲突询问）→ 写 marker

**三种项目形态**（本轮均支持），差异只在生效模板源：

- **多 stack（`len >= 2`）**：前端 / 后端正交叠加（如 `python-uv` 落根 + `react-vite` 落 `frontend/`），各 stack 按各自 `path` 落点 + `_common` 一并参与
- **单 stack（`len == 1`）**：`<stack>` + `_common` 两源参与
- **无 stack（`len == 0`）**：仅 `_common`，适用于模板源仓库本身（`claude-code-global`）或所有 stack 都不合身、但仍想复用 `_common` stack-无关资源（issue templates、`labels.yml`、`.prettierrc` 等）的项目

各 stack 的 `path` 来自 marker（bootstrap / adopt 按 `stack.yml` `default_path` 写入：`python-uv`→`.`、`react-vite`→`frontend`）。

**三态收敛约定（下文统一遵循、不再逐处复述）**：凡「遍历 stacks」对每条 stack 各跑一遍；`len == 1` 退化为单条、**行为与旧单 stack 完全一致**；`len == 0` 走「仅 `_common`」分支。skipped 读写位置随形态而定——`len >= 1` 用 `stacks[].skipped`（`_common` 归 `stacks[0]`），`len == 0` 用 marker 顶层 `skipped`（不为 `_common` 造虚拟 stack 条目，以免破坏「`_common` 不进 stacks 列表」约定）。

详细 schema / 设计决策：`~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/`（SCHEMA.md / PROMPT.md / PLAN.md）

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

### 废弃 BACKLOG.md 一次性迁移

需求管理已改为「云端 issue 单一真源、无本地索引文件」（见 `GLOBAL_AGENTS.md`「需求管理」章）。老项目本地可能仍遗留 `docs/BACKLOG.md`——它与云端 open issues 是双写副本，正是新约定要消除的 drift。sync 是「把约定变更落地到老项目」的天然承载点，故在此做一次性迁移（做完即删文件、后续幂等无操作，类比上文「旧名 marker 自动迁移」）。

**探测**：项目根 `docs/BACKLOG.md` 是否存在。

- **不存在** → 跳过本节（绝大多数已迁移 / 新项目都走这里）。
- **存在** → 停下来引导用户一次性迁移，迁完再 `git rm`，然后继续正常 sync：
  1. **读 `docs/BACKLOG.md`**，分出两类条目：
     - **open 项**（`## P0/P1/P2` 段里的行，每行本就带一个云端 issue 链接）；
     - **「刻意不做」项**（`## 已完成 / 不再追踪` 段里的行，每条带原因）。
  2. **open 项 → 确认云端已有对应 issue**：逐条核对该行的 issue 链接指向的 issue 仍 open（`python3 $HOME/.claude/scripts/platform_issue.py issue-view <N>`）。都在 → 无需动作（云端已是真源，删文件不丢信息）；若某行**没有** issue 链接（极老的裸文本条目）→ 提示用户先 `/backlog` 把它补成云端 issue，再继续。
  3. **「刻意不做」项 → 归档为带 `wontfix` 的 closed issue**（与 `/finish` Step 2 同一手法）：逐条 `issue-create --title "刻意不做：<一句话>" --body-file <tmp> --label wontfix --label type:docs --label area:<Y> --label priority:P2`（body 保留原因文字），建完 `gh issue close <N> -r "not planned"`（GitLab 用 `glab issue close <N>`）。`wontfix` label 缺失先补进 `.github/labels.yml` 并 sync。label 契约见 `~/.claude/scripts/platform_issue.md`。
  4. **删文件**：两类条目都迁移确认后 `git rm docs/BACKLOG.md`，告知用户「已废弃本地 BACKLOG.md，open 项速览改用 saved query（按 priority 过滤 open issues），刻意不做项已归档为 wontfix closed issue」。
  5. 迁移完成后**继续**下面的模式判断，把本轮 sync 正常跑完（BACKLOG.md 的删除会一并进本轮 sync 的收尾 diff）。

### 判断模式

读项目根 `.agent-template.yml`：

- **不存在** → 进入第 4 节「Adopt 模式」
- **存在** → 进入第 2 节「Normal sync」

## 2. Normal sync：解析 marker + 计算变更

### 2.1 解析 marker

直接 Read 文件、按 YAML 语义读字段。需要：

- `template_commit`（旧 commit hash）
- `stacks` 列表（0、1 或多条）；每条读 `stack`（名）、`path`（落点）、`skipped`（数组）、`variants`（map: 变体落地目标名 → 选中 key，**可缺省**，缺省视作空 map —— 老项目 bootstrap 时还没这机制）
- `len == 0` 时改读 marker **顶层** `skipped`（数组，可缺省视作空数组）

**校验**：

- `stacks` 各条的 `path` 用其声明值（如 `python-uv`→`.`、`react-vite`→`frontend`），不再强制 `path == .`
- 同一 marker 内不应出现重复 `stack` 名或重复 `path`，若有 → 报错并请用户手动修

（后续 2.x / 6.x 的「遍历 stacks」「`<stack>`」按顶部「三态收敛约定」处理。）

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

**扫的模板源 = marker 里每个 stack 的 `templates/<stack>/` + 始终自动应用的 `_common/`**。把所有生效源作为 pathspec 一次性 diff：

```bash
# 例：marker 有 python-uv + react-vite 两条
git -C ~/.claude/global-repo diff --name-status <old>..<new> -- \
  templates/python-uv/ templates/react-vite/ templates/_common/
```

- `len == 1`：`templates/<stack>/ templates/_common/`（等价旧单 stack）
- `len == 0`：仅 `templates/_common/`

⚠️ 不要省略 pathspec：`git diff` 不传路径会扫全 templates、误把项目未接入的其他 stack 的变更带进来。pathspec 只列 marker 里实际有的 stack。

输出形如：

- `M templates/python-uv/__root__/.gitignore`（修改，来源 stack）
- `A templates/_common/__root__/.github/ISSUE_TEMPLATE/feat.md`（新增，来源 \_common）
- `D templates/python-uv/__subpath__/configs/old.json`（删除）

若输出为空 → 报告「模板自上次同步起未变化」，再继续走 skipped 重检（2.5）。

### 2.4 对每个变更文件做四象限分析

对应到项目侧路径（**先按 diff 路径 `templates/<source>/...` 判定该文件来源是哪个 stack 或 `_common`**）：

- `__root__/<rel>` → 项目根的 `<rel>`（任何来源都落根）
- `__subpath__/<rel>` → 该来源 stack 的 `<path>/<rel>`（`python-uv` path `.` → 项目根；`react-vite` path `frontend` → `frontend/<rel>`）
- `_common` **理论上不应出 `__subpath__/` 内容**（设计约束：`_common` 只承载 stack-无关、根级资源）；若违反，按项目根 `<rel>` 兜底 + 输出警告

不同 stack 的 `__subpath__` 落到各自 `path` 子树、天然不撞；`__root__` 内容各 stack 与 \_common 共贡献到根，**不应有同名冲突**（设计约束）；万一有，stack 优先。

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

**特殊：变体组文件**（凡文件名形如 `<target>.variant.<key>`）永远不直接写同名文件——同一 `<target>` 的多个 `.variant.<key>` 是「一组互斥变体」，只有一个落地为 `<target>`（去 `.variant.<key>` 后缀，落该来源 stack 的落点）。normal sync 遇到某变体组文件有 diff（`M`/`A`/`D`）时，**先看 marker 里该 stack 的 `variants[<target>]` 记没记选择**：

- **有记录**（如 `variants[.gitlab-ci.yml] == shell`）→ **只处理选中 key（`shell`）那份变体**与项目侧已落地 `<target>` 的四象限（模板旧版 / 新版都取 `.variant.shell`，项目侧取 `<target>`）；**其余 key 的变体文件 diff 一律忽略**（用户没在用、不落地）。选中变体新增了 job / 改了脚本 → 按四象限（多半「模板改 + 项目侧已自定义或一致」）提议 take / merge 进项目侧 `<target>`。
- **无记录**（老项目 bootstrap 早于本机制，marker 无 `variants` 字段或缺该 target）→ 该变体组标记「需补选」，进 TODO；第 5 节决策时**问用户选一个 key**（展示各变体人话说明，key 说明由 skill 按已知 key 硬编码给，同 bootstrap Step 3.3.7），选后：① 用选中变体与项目侧 `<target>` 做四象限落地；② **把选择写回 marker** 对应 stack 的 `variants[<target>]`（6.1 持久化）。
- **变体文件被模板删除**（某 key 整个 `.variant.<key>` 从模板消失）→ 若正是当前选中 key，提示用户「所选变体已从模板移除，需改选其他变体」；非选中 key 则静默忽略。

> 各变体的人话说明（当前唯一变体组 `.gitlab-ci.yml`）：`docker` → "Docker executor runner"；`shell` → "本地 shell runner（无 docker executor，脚本装 uv）"。与 bootstrap Step 3.3.7 同一份，改动时两处同步。

**特殊：fragment 文件**（凡文件名以 `.fragment` 结尾）永远不直接写同名文件，去掉 `.fragment` 后缀得目标相对路径（始终落项目根），按目标类型**合并**。当前两类：

**(a) `pyproject.toml.<section>.fragment`（TOML 段合并）**

- 命名约定：`<section>` 用 `-` 分隔层级（如 `ruff` → `[tool.ruff]`、`uv` → `[tool.uv]`、`uv-index` → `[[tool.uv.index]]`、`uv-workspace` → `[tool.uv.workspace]`、`pytest` → `[tool.pytest.ini_options]`；以 fragment 内实际表头为准）。
- 合并语义：项目侧无此段 → 直接追加；已有此段 → AI 智能合并，保留用户自定义字段，模板新增字段追加；冲突字段询问用户。
- 数组段（双方括号，如 `[[tool.uv.index]]`）：按 `name` 字段 union（项目侧已有同名条目则跳过，避免重复注册）。
- 项目无 `pyproject.toml`：
  - normal sync 路径 → 标记「skipped: 项目无 pyproject.toml」
  - adopt 路径下选了 `python-uv` stack → 标记为「待 4.4 完成 `uv init` 后合并」
  - adopt 路径下选了 `python-uv-workspace` stack → **直接用本 stack 的 workspace fragments 内容创建虚拟根 `pyproject.toml`**（虚拟根无 `[project]`、不该 `uv init`），**不**等 4.4
  - 其他情况仍按 skipped 处理

**(b) `.vscode/<name>.json.fragment`（JSON 合并，目标项目根 `.vscode/<name>.json`）**

- 目标**不存在** → 用 fragment 内容创建（含父目录）。
- 目标**已存在** → 按目标语义合并：`extensions.json` 的 `recommendations` 数组做**有序去重 union**；`settings.json` 对象做**顶层键 union**（键只一侧→并入；两侧都为对象→递归深合并；标量冲突→询问）。
- 多个 stack 的同名 `.vscode/<name>.json.fragment` 依次合并进**同一个**项目根目标，得各 stack 推荐 / 设置的并集（前后端语言作用域键天然不相交，纯 union）。之所以汇聚到项目根：VS Code 单根工作区只读仓库根的 `.vscode/`，子目录 stack 也须借此落根。

**fragment 迁移去重（重要）**：当模板把某资源从「`__subpath__` 普通文件」改为「`__root__/*.fragment`」时，diff 会同时出现「`D __subpath__/X`」与「`A __root__/X.fragment`」。判断二者**目标项目路径是否相同**：

- **相同**（如 `python-uv` 的 `__subpath__/.vscode/settings.json`（path `.` → 根）与新 `__root__/.vscode/settings.json.fragment`（→ 根）目标都是根 `.vscode/settings.json`）→ 判为**机制迁移而非真删除**：**抑制删除提案**，仅执行 fragment 合并（content 不变时合并为幂等 no-op，原文件原样保留）。
- **不同**（如 `react-vite` 的 `__subpath__/.vscode/*`（path `frontend` → `frontend/.vscode/`）与新根 `.vscode/*.fragment`（→ 根））→ 二者互不矛盾：照常提案删除旧 `frontend/.vscode/*` + fragment 合并进根 `.vscode/*`。

**普通文件 → 变体组 迁移去重（重要）**：当模板把某资源从「普通文件 `X`」改为「一组变体 `X.variant.<key>`」时（如本机制把 `.gitlab-ci.yml` 改为 `.gitlab-ci.yml.variant.docker` / `.variant.shell`），老项目 normal sync 的 diff 会同时出现「`D X`」与多个「`A X.variant.<key>`」。这些变体的落地目标都是同一个 `<target> == X`（去 `.variant.<key>` 后缀），故：

- **判为机制迁移而非真删除**：**抑制对 `X` 的删除提案**（项目侧已落地的 `X` 就是那份要保留 / 更新的目标文件，不能删）。
- 改为按上文「特殊：变体组文件」处理这组 `A X.variant.<key>`：marker 有该 target 选择 → 用选中变体与项目侧 `X` 四象限；marker 无（这类老项目 marker 必然无 `variants`）→ 标记「需补选」，第 5 节问用户选一个、落地 + 写回 marker。
- 净效果：老项目从「一份写死的 `.gitlab-ci.yml`」平滑迁到「按 runner 选定的变体」，`.gitlab-ci.yml` 文件本身不被误删。

### 2.5 处理 skipped 持久化语义

skipped 读写位置按顶部「三态收敛约定」（`len >= 1` 归 `stacks[].skipped`、`len == 0` 归顶层 `skipped`）。汇总所有来源的 skipped 后，对每条做「是否又变过」重检：

- 取 `file`（含来源 source 段，如 `__root__/.github/labels.yml`） 与 `skipped_at_commit`
- 该文件实际来源（stack 或 \_common）由 skill 在分析阶段记录到 file 字段或动态确定
- 跑 `git -C ~/.claude/global-repo log --oneline <skipped_at_commit>..<new> -- templates/<source>/<file>`（`<source>` 是该文件实际来源 stack 或 \_common）
- 输出**为空**（该文件自 skip 之后未变） → **自动跳过、不进 TODO**
- 输出**非空**（变了） → **重新进 TODO**，标注「上次 skip 在 commit X，之后又改过」

### 2.6 输出 TODO 清单

每文件一项，含：序号 + 文件（来源段）、模板侧动作（M/A/D）、模板变化摘要、项目侧状态（是否已自定义 / 是否存在）、建议动作。示例：

```
[1] .gitignore （root）  M  新增 .ruff_cache/  | 项目侧已自定义(*.bak) → 智能 merge：保留 *.bak + 追加 .ruff_cache/
[2] .github/workflows/lint.yml （root）  A  | 项目侧不存在 → 创建
```

跳到第 5 节「用户批量决策」。

## 3. Normal sync 无变化退出条件

如果 2.3 输出空 + 2.5 没有"被重新提案的 skipped 项" + 没有需新增/删除的文件 → 报告「无需同步，模板与项目已对齐」并退出，不写 marker。

## 4. Adopt 模式（无 marker）

### 4.1 探测可用 stack

`~/.claude/templates/` 下非下划线开头的子目录列表。

### 4.2 用户选 stack（可多选）

先按 bootstrap Step 3.1 同法探测每个 stack 的 `default_path`（读 `templates/<stack>/stack.yml`，缺省 `.`）。询问用户：列出可选 stack，让其**勾选 0 个或多个**（前端 / 后端可叠加）。path 不询问，由各 stack 的 `default_path` 决定（`python-uv`→`.`、`react-vite`→`frontend`）。

**一个都不选 = 无 stack（只 \_common）**：仅复用 `_common` 的 stack-无关资源（issue templates、`labels.yml`、`.prettierrc` 等）。适用于模板源仓库本身（`claude-code-global`）或确认所有 stack 都不合身的项目。此时 4.3 仅扫 `_common/` 一个源，marker `stacks` 最终写为 `[]`。

### 4.3 全套用模板（含冲突询问）

**待新增的模板源由 4.2 选择决定**：

- 选了 1 个或多个 stack：`_common/` + 每个选定 `<stack>/` 的 `__root__/*` + `__subpath__/*` 全部当作"待新增"列入 TODO
  - `~/.claude/templates/_common/`（如存在，**自动应用**，`__root__` 落项目根）
  - 每个 `~/.claude/templates/<stack>/`：`__root__` 落项目根、`__subpath__` 落该 stack 的 `<default_path>/`（如 `react-vite`→`frontend/`）
- 一个都没选（无 stack）：仅 `~/.claude/templates/_common/` 一个源

判断：

- 项目侧不存在 → 默认建议「创建」
- 项目侧已存在 → AI 对比模板内容与项目内容：
  - 完全一致 → 默认建议「无需操作（已等价）」
  - 不一致 → 默认建议「智能 merge」或询问 take / 保留 / merge
- **变体组文件**（`<target>.variant.<key>`）：与 bootstrap Step 3.3.7 对称——同一 `<target>` 的多个变体**当作一条 TODO**「选一个变体落地」，第 5 节问用户选 key（展示人话说明），只把选中那份落地为 `<target>`、其余不落地；选择在 6.1 写进 marker 该 stack 的 `variants[<target>]`。项目侧已有 `<target>` → 冲突询问 take / 保留 / merge。
- `*.fragment`（`pyproject.toml.*.fragment` 与 `.vscode/*.json.fragment`）同 2.4 特殊处理
- 含 `.github/labels.yml` 时：**额外把"调 helper `label-sync-from-file` 同步 labels 到远端"作为单独一条 TODO**（helper 契约见 `~/.claude/scripts/platform_issue.md`）。

跳到第 5 节。

### 4.4 （选中含 python-uv 或 python-uv-workspace 时）后端项目实际可跑化

选中的 stack **既不含** `python-uv` **也不含** `python-uv-workspace` 则**整段跳过**。命中其一时（落点 path 均 `.`，下列命令在项目根执行），**先询问用户确认是否执行**（默认 yes，给「只要配置不要装依赖」选项），yes 则按以下子步骤逐条执行；no 则跳过整段并把决策记录到收尾反馈。

逻辑等同 bootstrap 的 Step 3.5，区别在 adopt 模式下 `pyproject.toml` **更可能已存在**（老项目），4.4.1 跳过 `uv init` 是常态。`python-uv` 与 `python-uv-workspace` **互斥**，正常只命中其一。

#### 4.4.1 确保 pyproject.toml 存在

**单包 `python-uv`**：

```bash
[ -f pyproject.toml ] && echo "exists, skip uv init" || uv init --package
```

`--package` 落标准 src 布局（`src/<pkg>/__init__.py` 空文件 + `[build-system] uv_build` 的 `pyproject.toml`），见 `playbooks/python.md` §2。adopt 下 `pyproject.toml` 多半已存在、本步 no-op。

**多包 `python-uv-workspace`**：**绝不 `uv init --package`**（会在虚拟根写 `[project]` + `src/` 破坏 workspace 形态）。虚拟根 `pyproject.toml` 由本 stack 的 workspace fragments 合并而成、成员包随模板 `packages/*` 复制就位；本步只确保上述 fragments 已合（2.4 的 TOML 段合并对「目标不存在」会用 fragment 内容创建根 `pyproject.toml`）。

跑完后回处理 2.4 标记「待 4.4 后合并」的所有 `pyproject.toml.*.fragment`（清华源段必须先合，否则 4.4.2 在国内会卡）。

#### 4.4.2 装常用 dev 依赖

```bash
uv add --dev pytest pytest-cov ruff
```

uv 会跳过已装的，幂等。失败 → 报告 stdout/stderr，提示用户手动重试 + 暂停 skill，**不**自动回滚已写文件。

> **`python-uv-workspace`**：`uv add --dev` 在虚拟根同样写入根 `[dependency-groups] dev` 并触发一次 `uv sync`，把 `packages/*` 各成员 editable 装入、解析跨成员 `workspace=true` 依赖——本步即让整个工作区可跑。

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

### 4.5 （选中含 react-vite 时）前端依赖安装

选中的 stack **不含** `react-vite` 则**整段跳过**。含 `react-vite` 时，前端模板（含 `package.json` + 固化 npmmirror 源的 `.npmrc`）已在 4.3 当作待新增列入 TODO、第 6 节执行后落到 `frontend/`。**先询问用户确认是否执行**（默认 yes，给「只要文件不装依赖」选项）：

```bash
cd frontend && npm install
```

失败 → 报告 stdout/stderr，提示用户手动重试，**不**自动回滚。装完可选 `npm run lint` / `npm run build` 验证。

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
- **accept (.vscode JSON 合并)**：把 `.vscode/<name>.json.fragment` 合并进项目根 `.vscode/<name>.json`（按 2.4 (b) 合并语义：`recommendations` 数组 union / `settings.json` 顶层键 union）
- **accept (label sync)**：调 helper 自动按平台 dispatch，exit 2/3/4 按契约降级、不阻塞其他 accept 项：

  ```bash
  python3 $HOME/.claude/scripts/platform_issue.py label-sync-from-file .github/labels.yml
  ```

  helper 完整行为（gh/glab dispatch、color 转换、exit code 降级、stdout TSV）见 `~/.claude/scripts/platform_issue.md`。

- **accept (变体落地 / 补选)**：把选中 key 的 `<target>.variant.<key>` 内容落地为 `<target>`（或按四象限 merge 进已存在的 `<target>`），其余变体不落地；把「`<target>` → 选中 key」写进对应 stack 的 `variants` map（6.1 持久化）。补选场景（老项目 marker 无记录）同理，落地 + 写 marker 一并完成。
- **skip**：在 marker 的 skipped 列表（位置按「三态收敛约定」）追加 / 更新条目，字段：`file`、`skipped_at_commit: <NEW_COMMIT>`、`reason: <可选>`

注意：skipped[] 的更新策略：

- 已在 skipped[] 中且本次仍 skip → 更新 `skipped_at_commit` 为 `NEW_COMMIT`
- 已在 skipped[] 中但本次 accept（即用户改主意了）→ 从 skipped[] 移除
- 不在 skipped[] 中且本次新 skip → 追加新条目

### 6.1 更新 marker

回写 `.agent-template.yml`：

- `template_commit` 更新为 `NEW_COMMIT`
- `bootstrap_time` 不动（这是首次 bootstrap 时间）
- `source` 不动
- skipped 按 6 节策略 + 「三态收敛约定」的位置更新
- `variants` 按 6 节「accept (变体落地 / 补选)」更新：**保留 marker 已有的变体选择**（本次未触及的不动）；本次落地 / 补选 / 改选的变体写 / 更新对应 stack 的 `variants[<target>]`。无任何变体组的 stack 不写该字段。

Adopt 模式额外：

- `bootstrap_time` 设为当前 ISO 时间
- `source` 取 `git -C ~/.claude/global-repo config --get remote.origin.url`，无则填占位
- `stacks` 按 4.2 用户选择写，每条 `path` 取该 stack 的 `default_path`；落了变体组的 stack 增写 `variants` map（4.3 的变体落地选择）：
  - 选了 1 个或多个 stack → 每个一条，如 `[{stack: python-uv, path: ".", skipped: [], variants: {.gitlab-ci.yml: shell}}, {stack: react-vite, path: "frontend", skipped: []}]`
  - 一个都没选（无 stack）→ `stacks: []`，同时顶层加 `skipped: []`

### 6.2 收尾反馈

列出实际改动的项目侧文件清单（path-by-path），提示用户：

1. `git diff` 自行 review
2. 如新加入的 `.pre-commit-config.yaml` 还未生效，跑 `pre-commit install`（adopt 模式 4.4 已自动做过；normal sync 不做）；可选跑 `pre-commit run --all-files` 验证
3. 满意后用 `/commit` 或自行 `git commit`

**不自动 commit** —— 由用户决策（与 `/bootstrap`、`/backlog` 一致）。
