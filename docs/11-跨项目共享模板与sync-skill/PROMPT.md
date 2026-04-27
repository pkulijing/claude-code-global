# PROMPT：跨项目共享模板与 sync skill

## 背景

上一轮（commit `feat(11): 加 lint 闸门`）补齐了 lint 拦截链中的两环：

- 编辑器/AI 编辑后：`PostToolUse` hook（`fix-after-edit.sh` = `ruff check --fix` + `ruff format`）
- AI commit 闸门：`/commit` skill 提交前跑项目 lint，失败显式让用户决策

但调研业界做法后发现真正的 lint 拦截链是**四层**：

| 层 | 触发 | 工具 |
|---|---|---|
| 1. 编辑器内 LSP | 保存 | `ruff server` |
| 2. AI 编辑后 hook | CC PostToolUse | ✓ 已实现 |
| 3. commit 前 | `git commit` | **pre-commit framework + `astral-sh/ruff-pre-commit`** |
| 4. CI | push / PR | GitHub Actions |

第 3、4 两层都是**项目级配置**（`.pre-commit-config.yaml` 在项目根、`.github/workflows/lint.yml` 在项目 `.github/`），**不属于 CC 配置范畴**。这暴露了一个更宏观的问题：

> 除了 CC 自身配置外，还有一类"**跨项目共用的开发配置**"（pre-commit、`.vscode/`、CI、`pyproject.toml` 的 ruff 段、`.gitignore` 等）需要一套统一的管理机制。否则每个新项目都要手动重做、老项目同步靠记忆。

## 目标

把 `claude-code-global` 仓库**单仓库统管**两类资源：

1. **CC 自身配置**（现状不变）：`GLOBAL_CLAUDE.md` / `settings.base.json` / `hooks/` / `skills/`
2. **跨项目共享开发配置模板**（本轮新增）：`templates/<stack>/`

通过两个 skill 入口完成 propagate：
- `/bootstrap`：新项目 → 选 stack → 复制模板 → 写 marker
- `/sync-project-config`（**新增**）：老项目 → 读 marker → AI 智能 merge 分析 → TODO → 用户批量决策 → 执行 → 回写 marker

不拆出第二个仓库。

## 架构决策（已 frozen）

讨论中按 Q1~Q8 拍板：

### Q1. 模板颗粒度：按 stack 切

`templates/python-uv/`、`templates/node/`、`templates/_common/`（语言无关）等。颗粒度粗，避免组合爆炸。

### Q2. sync 行为模型：AI 智能分析 + 用户批量决策

骨架：
1. 探测当前项目 stack → 选定 `templates/<stack>/`
2. **AI 对每个模板文件做差异分析**（含 vs 项目现状的 diff、解读项目是否合理偏离）
3. 输出 TODO 清单（per-file 一条，附 diff 摘要 + AI 建议的合并方式）
4. 用户对清单 **一次性批量决策** accept / skip
5. 执行 + 列出最终改动 + 提示用户 review 后 commit

### Q3 & Q7. Marker 文件

文件名：`.cc-template.yml`，**项目根目录**，**commit 进 git**。

字段（人/机器都可读，schema 已为多 stack 项目设计，单 stack 项目降级为只含一项的 `stacks` 列表）：

```yaml
# 由 claude-code-global 管理，非必要请勿手动编辑
source: https://github.com/<user>/claude-code-global
template_commit: <最后一次同步到的 templates 的 commit hash>
bootstrap_time: <ISO timestamp>
stacks:
  - stack: python-uv
    path: .                       # 单 stack 项目恒为 "."；多 stack 项目为 "backend"/"frontend" 等
    skipped:
      - file: .vscode/settings.json
        skipped_at_commit: <当时模板 commit>
        reason: <可选，用户填>
```

`source` 用字段而非纯注释，未来支持多源/fork 检测；顶部一行注释提示来源。

### Q9 & Q10 & Q11. 多 stack 支持（schema 前瞻、本轮单 stack 实现）

**真实场景**：monorepo 项目可能在不同子目录使用不同 stack，例如 `frontend/`（React）+ `backend/`（python-uv），通过 VS Code multi-root workspace 管理。

**文件 scope 分类**（每个模板文件二选一）：

- **`__root__`-scoped**：写到 git 根目录。多 stack 项目里，**多个 stack 共同贡献到同一个根文件**（如 `.pre-commit-config.yaml` 同时挂 ruff + eslint），需要 AI 跨 stack merge 才能产出最终内容
- **`__subpath__`-scoped**：写到 `<subpath>/`。stack 间互不干扰，每个 stack 在自己的 subpath 下独立

**python-uv stack 的初步分类**：

| 文件 | scope |
|---|---|
| `.pre-commit-config.yaml` | `__root__` |
| `.gitignore` | `__root__` |
| `.github/workflows/lint.yml` | `__root__` |
| `.prettierrc` | `__root__` |
| `pyproject.toml.ruff.fragment` | `__subpath__` |
| `.vscode/settings.json` | `__subpath__` |
| `.vscode/extensions.json` | `__subpath__` |

`.vscode/` 归 `__subpath__` —— 多 stack monorepo 时每个 subdir 各自有自己的 `.vscode/`，配合 multi-root workspace 用法。

**templates 目录结构**：

```
templates/
└── python-uv/
    ├── __root__/
    │   ├── .pre-commit-config.yaml
    │   ├── .gitignore
    │   ├── .prettierrc
    │   └── .github/workflows/lint.yml
    └── __subpath__/
        ├── pyproject.toml.ruff.fragment
        └── .vscode/
            ├── settings.json
            └── extensions.json
```

**关于"多 stack 时 root 文件归属"**：根文件按 stack 组织（住在 `templates/<stack>/__root__/`），表达的是"这个 stack 对根文件的贡献"。

- 单 stack 项目：那一份 `__root__` 内容整体复制到 git 根
- 多 stack 项目（**本轮不实现**）：多个 stack 的 `__root__` 同名文件由 AI smart-merge 后写到根

未来"完全 stack-无关"的根文件（如通用 OS gitignore、通用 prettierrc）可放到 `templates/_common/__root__/`，由 `_common` 这个伪 stack 承载，不需新机制。

**本轮范围（Q9）**：

- Marker schema **已为多 stack 设计**（`stacks` 是列表）
- bootstrap / sync 实现层面 **断言只接受单 stack** —— `stacks` 列表恰好 1 项、`path` 必须是 `.`，否则报错并提示"多 stack 支持在后续 round"
- 多 stack 跨 stack merge 逻辑、`_common` 伪 stack 等留下一轮

### Q4. Merge 策略：AI 智能分析，不机械

总体原则是 merge，但**不是机械 merge**。每个文件由 AI 现场判断采用哪种合并方式（追加 / 段级合并 / 全替 / 跳过），作为 TODO 项中的"建议"呈现给用户。

### Q5. Placeholder 处理：折中方案

- bootstrap 时填值后写入（如项目名、Python 版本）
- sync **不碰**带值的部分，避免重置用户已填好的内容
- 模板里凡是含 placeholder 的文件 / 段，sync 阶段 skip

### Q6. Legacy 项目（无 marker）：sync 自带 adopt 模式

sync 检测到无 `.cc-template.yml` → 进入 **adopt 分支**：让用户选 stack → 当作"全是新增"完整写入 → 生成 marker。bootstrap 仍专管"空目录"语义不混。

### Q7-2. Skipped 持久化语义：B 方案（带 commit）

`skipped[]` 中每条记录"在 template_commit X 时 skip 了它"。后续 sync 时：
- 模板那条**继续没动** → 自动跳过，不重提
- 模板那条**变了** → 重新提案（可能用户当初 skip 是因为旧版有问题，新版可能能接受）

### Q8. sync 访问 templates git 历史：方案 C

`install.sh` 新增软链 `~/.claude/global-repo` → `claude-code-global` 仓库根。sync skill 通过这条软链 `git -C ~/.claude/global-repo diff X..Y -- templates/<stack>/` 拿到模板版本变化。

## 范围

### 包含

- 新增 `templates/` 目录及 **`python-uv` stack 的初版**（按 `__root__` / `__subpath__` 分组）：
  - `__root__/.pre-commit-config.yaml`（含 `astral-sh/ruff-pre-commit` 的 `ruff-check` + `ruff-format` hook，不带 `--fix`）
  - `__root__/.gitignore`（Python + uv 常见模式）
  - `__root__/.github/workflows/lint.yml`（先 inline jobs，后续可换成 reusable workflow）
  - `__root__/.prettierrc`（`{ "proseWrap": "preserve" }`，已在 GLOBAL_CLAUDE.md 推荐）
  - `__subpath__/pyproject.toml.ruff.fragment`（`[tool.ruff]` 段，bootstrap 时合并进项目 `pyproject.toml`）
  - `__subpath__/.vscode/settings.json`（formatOnSave + ruff source.fixAll）
  - `__subpath__/.vscode/extensions.json`（推荐 charliermarsh.ruff 等）
- `install.sh` 扩展：
  - 软链 `templates/` → `~/.claude/templates/`
  - 软链仓库根 → `~/.claude/global-repo`
- 新增 `/sync-project-config` skill：
  - 检测 marker → 走正常 sync / 走 adopt
  - 断言 `stacks` 列表恰好 1 项、`path` = `.`（多 stack 报错并提示后续 round 支持）
  - AI 分析 → TODO → 用户决策 → 执行 → 回写 marker
  - 处理 `skipped` 持久化语义
- 扩展 `/bootstrap` skill：选 stack → 按 `__root__` / `__subpath__` scope 复制模板 + 填 placeholder → 写 `.cc-template.yml` marker（`stacks` 1 项、`path: .`）
- 定义 `.cc-template.yml` 的 schema 文档（写到 PLAN.md 或单独 SCHEMA.md）

### 不包含

- `_common`、`node` 等其他 stack（先把 python-uv 一条路跑通，再按需扩）
- **多 stack monorepo 支持**（schema 已为其设计，但本轮 bootstrap/sync 只接受单 stack；未来 round 实现 AI 跨 stack merge）
- GitHub `<user>/.github` 仓库的 reusable workflows 实际部署（templates 里的 `lint.yml` 先用 inline，后续迁移）
- 已有项目的 mass migration（sync skill 可用后由用户按需进各项目跑）
- per-hunk 粒度的 sync 决策（per-file 足够，更细的等真实需求驱动）

## 验收

1. **bootstrap 路径**：空目录跑 `/bootstrap` 选 python-uv → 项目根有完整的 `.pre-commit-config.yaml`、`.vscode/`、`.gitignore`、`pyproject.toml` 含 ruff 段、`.github/workflows/lint.yml`、`.cc-template.yml`
2. **pre-commit 验证**：项目里 `pre-commit install && pre-commit run --all-files` 通过
3. **正常 sync 路径**：修改 `templates/python-uv/.pre-commit-config.yaml` 一行 → 进项目跑 `/sync-project-config` → AI 列出 TODO 含这条 → accept → 项目侧文件被更新、marker `template_commit` 推进到当前 HEAD
4. **adopt 路径**：另一个无 marker 的老项目跑 `/sync-project-config` → 进入 adopt 模式 → 选 stack → 完整写入 + 生成 marker
5. **skipped 持久化**：用户在 sync 中 skip 一条 → 下次 sync 时模板若未变化则不再提案；若模板那条变了则重新提案

## 后续 TODO（不在本轮）

- **多 stack monorepo 支持**：bootstrap 支持反复添加 stack（不同 subpath）；sync 处理 `stacks` 多项；AI 实现跨 stack 的 root 文件 merge（如 `.pre-commit-config.yaml` 同时挂多语言 hook、CI workflow 跑矩阵）
- 增加 `_common`、`node` 等其他 stack（`_common` 作为伪 stack 承载完全 stack-无关的根文件）
- 部署 `<user>/.github` 仓库的 reusable workflows，把项目里的 `lint.yml` 改成 `uses:` 引用
- 项目侧"marker 校验" hook（每次 commit 验证 `.cc-template.yml` 存在 + 字段合规）
- sync 的 dry-run 模式（只列 TODO 不执行）
