---
name: sync-project-config
description: 把 claude-code-global 仓库管理的"跨项目共享开发配置模板"的最新变化同步进当前项目；含 adopt 模式（无 marker 老项目首次接入）
disable-model-invocation: false
---

把 `~/.claude/templates/` 的变化反映到当前项目。两种模式：

- **Normal sync**（项目根有 `.agent-template.yml` marker）：算 diff → 智能 merge 提议 → 用户批量决策 → 执行
- **Adopt**（无 marker）：让用户选 stack → 当作「全是新增」完整套用一次 → 写 marker

**动手改文件前先读 `templates/MECHANICS.md`** —— 落点语义（`__root__` / `__subpath__` / `_common`）、fragment 合并、变体组落地、后端可跑化、前端装依赖、迁移去重全在那里，本 skill 不复述。字段 schema 与设计取舍见 `~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/`。

**三态收敛约定**（下文统一遵循、不再逐处复述）：marker 的 `stacks` 可以有 0、1 或多条。凡「遍历 stacks」对每条各跑一遍；`len == 1` 退化为单条、行为与旧单 stack 完全一致；`len == 0` 走「仅 `_common`」分支。skipped 的读写位置随形态而定 —— `len >= 1` 用 `stacks[].skipped`（`_common` 归 `stacks[0]`），`len == 0` 用 marker **顶层** `skipped`（不为 `_common` 造虚拟 stack 条目，以免破坏「`_common` 不进 stacks 列表」的约定）。

`len == 0` 的用途：模板源仓库自身（`claude-code-global`），或所有 stack 都不合身、但仍想复用 `_common` 的 stack-无关资源的项目。

## 前置检查

按顺序，**任一失败立即停止并报告**：

- 当前目录是 git 仓库（`git rev-parse --is-inside-work-tree`）
- `~/.claude/templates/` 存在且至少含一个 stack 子目录
- `~/.claude/global-repo/` 存在、是指向本仓库的软链、且能跑 `git rev-parse HEAD`

失败 → 提示用户重跑 `bash ~/.claude/global-repo/install.sh` 并退出。

## 模式判断

### 旧名 marker 自动迁移

marker 文件名在 round 22 由 `.cc-template.yml` 改为 `.agent-template.yml`。读 marker 前先查：

- 只有旧名 → `git mv .cc-template.yml .agent-template.yml`，并明确告知用户已自动迁移
- **两者同时存在** → 报冲突并停止，请用户手动处理（不猜哪个为准）

### 废弃 BACKLOG.md 一次性迁移

需求管理已改为「云端 issue 单一真源、无本地索引文件」（见 `GLOBAL_AGENTS.md`）。老项目遗留的 `docs/BACKLOG.md` 与云端 open issues 是双写副本，正是新约定要消除的 drift；sync 是「把约定变更落地到老项目」的天然承载点。

项目根无 `docs/BACKLOG.md` → 跳过本节（绝大多数项目走这里）。有则停下来引导一次性迁移，迁完 `git rm` 再继续正常 sync：

1. 读文件，分出 **open 项**（`## P0/P1/P2` 段，每行本就带云端 issue 链接）与**「刻意不做」项**（`## 已完成 / 不再追踪` 段，每条带原因）。
2. **open 项**：逐条核对链接指向的 issue 仍 open（`python3 $HOME/.claude/scripts/platform_issue.py issue-view <N>`）。都在 → 无需动作（云端已是真源，删文件不丢信息）。某行**没有** issue 链接（极老的裸文本条目）→ 提示用户先 `/backlog` 补成云端 issue 再继续。
3. **「刻意不做」项** → 按 `/finish` Step 2 的同一手法归档为带 `wontfix` 的 closed issue（body 保留原因文字）。
4. `git rm docs/BACKLOG.md`，告知用户：open 项速览改用 saved query，刻意不做项已归档为 wontfix closed issue。
5. 继续下面的模式判断，把本轮 sync 正常跑完（文件删除会一并进本轮收尾 diff）。

### 判断模式

读项目根 `.agent-template.yml`：不存在 → 第 4 节 Adopt；存在 → 第 2 节 Normal sync。

## 2. Normal sync：解析 marker + 计算变更

### 2.1 解析 marker

直接 Read、按 YAML 语义读：`template_commit`（旧 commit hash）、`stacks` 列表（每条读 `stack` / `path` / `skipped` / `variants`——`variants` 可缺省，视作空 map，老项目 bootstrap 时还没这机制）。

**校验**：各条 `path` 用其声明值（不再强制 `path == .`）；同一 marker 内出现重复 `stack` 名或重复 `path` → 报错请用户手动修。

### 2.2 拿当前模板 HEAD

```bash
NEW_COMMIT=$(git -C ~/.claude/global-repo rev-parse HEAD)
```

`git -C ~/.claude/global-repo status --porcelain templates/` 非空 → 警告用户「templates 有未提交修改，sync 仅基于 HEAD，未提交内容不会同步」。

### 2.3 计算模板变更

**生效模板源 = marker 里每个 stack 的 `templates/<stack>/` + 始终自动应用的 `_common/`**。把所有生效源作为 pathspec 一次性 diff：

```bash
git -C ~/.claude/global-repo diff --name-status <old>..<new> -- \
  templates/python-uv/ templates/react-vite/ templates/_common/
```

⚠️ **不要省略 pathspec** —— 不传路径会扫全 templates，把项目未接入的其他 stack 的变更也带进来。pathspec 只列 marker 里实际有的 stack。

输出为空 → 报告「模板自上次同步起未变化」，仍继续走 2.5 的 skipped 重检。

### 2.4 对每个变更文件做四象限分析

**先按 diff 路径 `templates/<source>/...` 判定来源是哪个 stack 或 `_common`**，再按 `templates/MECHANICS.md` §1 映射到项目侧路径。

读 3 份内容做对比：模板旧版 `git -C ~/.claude/global-repo show <old>:templates/<source>/<scope>/<rel>`、模板新版（直接读 `~/.claude/templates/...`）、项目侧现状（直接 Read）。

| 模板侧 | 项目侧 | 默认建议 |
| --- | --- | --- |
| 修改 | 与旧模板一致（未自定义） | take 新模板（clean update） |
| 修改 | 与旧模板不一致（已自定义） | AI 智能 merge：保留用户修改语义 + 引入模板新内容 |
| 新增 | 不存在 | 创建 |
| 新增 | 已存在（罕见） | 询问 take / 保留 / 智能 merge |
| 删除 | 仍存在 | 询问删除 / 保留（用户可能仍需要） |

**三类特殊文件按 `templates/MECHANICS.md` 处理**，都不走上表的普通路径：

- **`*.fragment`**（§2）：永远合并进目标、不落地为同名文件。
- **`<target>.variant.<key>`**（§3）：先看 marker 里该 stack 的 `variants[<target>]` 记没记选择。**有记录** → 只处理选中 key 那份变体与项目侧已落地 `<target>` 的四象限，其余 key 的 diff 一律忽略（用户没在用）。**无记录**（老项目）→ 标记「需补选」进 TODO，第 5 节问用户选一个，落地 + 写回 marker。
- **迁移去重**（§6）：diff 同时出现「删旧的」和「加新的」时，判断二者目标项目路径是否相同，相同则抑制删除提案。

### 2.5 处理 skipped 持久化语义

skipped 的读写位置按顶部「三态收敛约定」。汇总所有来源的 skipped 后，对每条做「是否又变过」重检：

```bash
git -C ~/.claude/global-repo log --oneline <skipped_at_commit>..<new> -- templates/<source>/<file>
```

输出**为空**（自 skip 后未变）→ 自动跳过、不进 TODO；**非空**（又改过）→ 重新进 TODO，标注「上次 skip 在 commit X，之后又改过」。

### 2.6 输出 TODO 清单

每文件一项：序号 + 文件（来源段）+ 模板侧动作（M/A/D）+ 变化摘要 + 项目侧状态 + 建议动作。

```
[1] .gitignore （root）  M  新增 .ruff_cache/  | 项目侧已自定义(*.bak) → 智能 merge：保留 *.bak + 追加 .ruff_cache/
[2] .github/workflows/lint.yml （root）  A  | 项目侧不存在 → 创建
```

跳到第 5 节。

## 3. Normal sync 无变化退出条件

2.3 输出空 + 2.5 无被重新提案的 skipped 项 + 无需新增/删除的文件 → 报告「无需同步，模板与项目已对齐」并退出，**不写 marker**。

## 4. Adopt 模式（无 marker）

### 4.1–4.2 探测并选 stack

同 `/bootstrap` 3.1–3.2：列出 `~/.claude/templates/` 下非下划线开头的子目录，按各自 `stack.yml` 的 `default_path` 决定落点，让用户**勾选 0 个或多个**。一个都不选 = 无 stack（只 `_common`），marker `stacks` 最终写 `[]`。

### 4.3 全套用模板（含冲突询问）

把生效源（`_common/` + 每个选定 `<stack>/`）的 `__root__/*` 与 `__subpath__/*` 全部当作「待新增」列入 TODO。判断：

- 项目侧不存在 → 建议「创建」
- 项目侧已存在 → 对比内容：完全一致 → 「无需操作（已等价）」；不一致 → 建议智能 merge 或询问 take / 保留 / merge

`*.fragment` 与变体组按 2.4 的特殊处理（同一 `<target>` 的多个变体**当作一条 TODO**「选一个落地」，第 5 节问用户选 key）。含 `.github/labels.yml` 时**额外把「调 helper `label-sync-from-file` 同步 labels」作为单独一条 TODO**。

### 4.4 / 4.5 可跑化与装依赖

选中含 `python-uv` / `python-uv-workspace` → 按 `templates/MECHANICS.md` §4 走后端可跑化；选中含 `react-vite` → 按 §5 装前端依赖。都是先问用户确认（默认 yes，给「只要配置不要装依赖」选项）。

adopt 与 bootstrap 的唯一差别：这里 `pyproject.toml` **更可能已存在**（老项目），§4 第 1 步跳过 `uv init` 是常态。

跳到第 5 节。

## 5. 用户批量决策

呈现 2.6 / 4.3 的 TODO，让用户给**统一指令**，例如：

> 「全部 accept；第 3 条 skip；第 5 条改成全替模板，不要 merge」

解析指令、产出最终执行计划，**再次回显**（per-file 写出每条最终动作）让用户显式确认后才执行。

## 6. 执行

按确认后的计划逐条执行：新增写文件、修改/智能 merge 用 Edit/Write 写回、删除删文件；fragment 与变体组按 `templates/MECHANICS.md` 落地。

**label sync** 项调 helper（exit 2/3/4 按契约降级、不阻塞其他 accept 项）：

```bash
python3 $HOME/.claude/scripts/platform_issue.py label-sync-from-file .github/labels.yml
```

**skip** 项在 marker 的 skipped 列表（位置按「三态收敛约定」）记 `file` / `skipped_at_commit: <NEW_COMMIT>` / `reason`。更新策略：已在列表且本次仍 skip → 更新 commit；已在列表但本次 accept（用户改主意）→ 移除；不在列表且本次新 skip → 追加。

### 6.1 更新 marker

回写 `.agent-template.yml`：`template_commit` 更新为 `NEW_COMMIT`；`bootstrap_time` 与 `source` 不动；skipped 按上述策略更新；`variants` **保留 marker 已有的选择**（本次未触及的不动），本次落地 / 补选 / 改选的写进对应 stack。

Adopt 模式额外：`bootstrap_time` 设为当前 ISO 时间；`source` 取 `git -C ~/.claude/global-repo config --get remote.origin.url`（无则填占位）；`stacks` 按 4.2 的选择写，每条 `path` 取该 stack 的 `default_path`。

### 6.2 收尾反馈

列出实际改动的项目侧文件清单，提示用户：① `git diff` 自行 review；② 新加入的 `.pre-commit-config.yaml` 若还没生效，跑 `pre-commit install`（adopt 的 4.4 已自动做过，normal sync 不做），可选 `pre-commit run --all-files` 验证；③ 满意后 `/commit`。

**不自动 commit** —— 由用户决策（与 `/bootstrap`、`/backlog` 一致）。
