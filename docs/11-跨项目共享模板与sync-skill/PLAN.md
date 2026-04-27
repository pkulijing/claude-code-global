# PLAN: 跨项目共享模板与 sync skill

> 详细需求见 [docs/11-跨项目共享模板与sync-skill/PROMPT.md](/Users/jing/Developer/claude-code-global/docs/11-跨项目共享模板与sync-skill/PROMPT.md)。本文档只列实现路径，不重复架构论证。

## Context

`claude-code-global` 仓库一身二职，新增 `templates/<stack>/` 管"跨项目共享配置模板"，配套两个 skill 入口（扩展 `/bootstrap`、新增 `/sync-project-config`）。本轮只做单 stack 实现（`python-uv`），多 stack monorepo 留下一轮，但 marker schema 已为其设计。

关键设计（已 frozen）：

- **Marker**：`.cc-template.yml` 在项目根，含 `stacks: [...]` 列表 + `template_commit` + `skipped[]`（带 commit hash 持久化）
- **文件 scope**：每个模板文件归 `__root__/`（项目根）或 `__subpath__/`（stack 自己的 subdir）
- **AI 智能 merge**：sync 中 per-file diff 分析 + TODO 批量决策，不机械 replace
- **install.sh**：新增两条软链（templates/ → `~/.claude/templates/`、仓库根 → `~/.claude/global-repo`）
- **YAML 处理**：skills 由 AI 驱动，直接 Read/Write 文件即可，不引入 yq/yaml 库依赖

## 实现步骤（顺序）

### Step 1：创建 `templates/python-uv/` 模板内容

按 scope 分组，文件清单与内容设计要点：

#### `templates/python-uv/__root__/.pre-commit-config.yaml`

引用 `astral-sh/ruff-pre-commit`，**不带 `--fix`**（按业界共识：commit 阶段 hook 不修改 working tree，只报错；fix 由 PostToolUse hook 和编辑器 fix-on-save 完成）。顺序：`ruff-check` 先 → `ruff-format` 后（官方要求）。pinned version 用最近的稳定 tag。

#### `templates/python-uv/__root__/.gitignore`

Python + uv 常见模式：`__pycache__/`、`*.pyc`、`.venv/`、`uv.lock` 不在忽略（uv 推荐 commit lock）、`.env`、`.env.local`、`.pytest_cache/`、`.ruff_cache/`、`dist/`、`build/`、`*.egg-info/`。OS junk：`.DS_Store`、`Thumbs.db`。IDE：`.vscode/*.log`、`.idea/`。

#### `templates/python-uv/__root__/.github/workflows/lint.yml`

inline GitHub Actions：触发 push/pull_request，setup uv → `uv sync --frozen` → `uv run ruff check .` → `uv run ruff format --check .`。本轮不引用 reusable workflow，后续 round 切换。

#### `templates/python-uv/__root__/.prettierrc`

`{ "proseWrap": "preserve" }`，与 GLOBAL_CLAUDE.md 推荐对齐。

#### `templates/python-uv/__subpath__/pyproject.toml.ruff.fragment`

只是 `[tool.ruff]` 段（line-length / target-version / lint.select / lint.ignore 等通用配置）。bootstrap 时由 AI 智能合并进项目 `<path>/pyproject.toml`（如果项目无 pyproject.toml 则提示用户先 `uv init`）。

#### `templates/python-uv/__subpath__/.vscode/settings.json`

VS Code 推荐：`[python]` 块设 `formatOnSave + defaultFormatter: charliermarsh.ruff`、`editor.codeActionsOnSave: { "source.fixAll": "explicit", "source.organizeImports": "explicit" }`、`[markdown]` 块设 prettier。与 GLOBAL_CLAUDE.md 「项目本地推荐配置」段对齐。

#### `templates/python-uv/__subpath__/.vscode/extensions.json`

`recommendations: ["charliermarsh.ruff", "esbenp.prettier-vscode", "ms-python.python"]`。

### Step 2：扩展 `install.sh`

在主流程"链接 hooks"之后、"合并 settings"之前插入两段：

```bash
# 链接 templates/ 到 ~/.claude/templates/（让 skill 通过 stable 路径读模板）
if [ -d "$REPO_DIR/templates" ]; then
    link_item "$REPO_DIR/templates" "$TARGET_DIR/templates"
else
    warn "仓库中未找到 templates/ 目录，跳过"
fi

# 链接仓库根到 ~/.claude/global-repo（让 sync skill 通过 git 命令读模板版本历史）
link_item "$REPO_DIR" "$TARGET_DIR/global-repo"
```

复用现成的 `link_item` 函数，不引入新逻辑。

### Step 3：扩展 `skills/bootstrap/SKILL.md`

当前 bootstrap 在 5 步流程的 step 3 写 `.prettierrc`、step 4 调 `/devtree`。把 `.prettierrc` 步骤替换成更通用的"模板初始化"，并紧接 step 4 之前插入：

新增 Step 3.5: **模板初始化**

1. 检测 `~/.claude/templates/` 是否存在；不存在则跳过该步并提示用户重装
2. 列出可用 stacks（即 `~/.claude/templates/` 下的非下划线开头子目录）
3. AskUserQuestion 让用户选 stack（提供「跳过模板初始化」选项）
4. 若用户选了 stack：
   - 复制 `~/.claude/templates/<stack>/__root__/*` 到项目根（不含已存在文件，遇冲突询问用户）
   - 复制 `~/.claude/templates/<stack>/__subpath__/*` 到项目根（单 stack 项目 path = `.`）
   - 智能合并 `pyproject.toml.ruff.fragment` 到 `pyproject.toml` 的 `[tool.ruff]` 段（若项目无 pyproject.toml，提示先运行 `uv init`）
   - 写入 `.cc-template.yml` marker（schema 见 Step 4 末段）
5. 收尾反馈：列出新增/合并的文件
6. 步骤 5（旧 step 3）写 `.prettierrc` 删除 —— 已通过模板提供

更新 SKILL.md 的前置检查条款：仍然拒绝已有 `docs/N-` 的项目（这是 bootstrap 「空项目首次初始化」语义的核心），引导用户去 `/sync-project-config` 走 adopt 模式。

### Step 4：新增 `skills/sync-project-config/SKILL.md`

frontmatter：

```yaml
---
name: sync-project-config
description: 把 claude-code-global 模板的最新变化同步进当前项目（含 adopt 模式：为无 marker 老项目首次接入）。
disable-model-invocation: false
---
```

skill 主流程（中文撰写，结构对齐 `/commit` 的"分析 → 提案 → 用户确认 → 执行"）：

#### 0. 前置检查
- 当前目录必须是 git 仓库（`git rev-parse --is-inside-work-tree`）
- `~/.claude/templates/` 和 `~/.claude/global-repo` 都必须存在（否则提示重跑 install.sh）

#### 1. 检测模式：normal sync vs adopt

读 `.cc-template.yml`：
- 不存在 → **adopt 模式**（跳到第 4 节）
- 存在 → **normal sync**（继续第 2 节）

#### 2. Normal sync：解析 marker + 计算 diff

a. AI 直接读 `.cc-template.yml`（YAML 内容简单，不需要 yq）。
b. 断言：`stacks` 列表恰好 1 项、`stacks[0].path == "."`。否则报错「多 stack 监管在后续 round」并退出。
c. 拿到 `stacks[0].stack`、`stacks[0].skipped[]`、`template_commit`。
d. 通过 `~/.claude/global-repo` 计算模板变更：
   - `git -C ~/.claude/global-repo rev-parse HEAD` 拿当前 HEAD
   - `git -C ~/.claude/global-repo log --oneline <old>..HEAD -- templates/<stack>/` 看是否有变更
   - 若无变更且 skipped 列表中无需重提的项 → 报告「无需同步」退出
   - `git -C ~/.claude/global-repo diff <old>..HEAD -- templates/<stack>/` 拿 diff，按文件归类
e. **检查 working copy**：若 `git -C ~/.claude/global-repo status --porcelain templates/` 非空，警告用户"模板有未提交修改，sync 仅基于 HEAD 进行"。

#### 3. Normal sync：AI 智能分析 + TODO 输出

对每个有变更的模板文件，AI 做四象限判断：

| 模板侧变化 | 项目侧状态 | 默认建议 |
|---|---|---|
| 修改 | 与旧模板版本一致（未自定义） | take 新模板 |
| 修改 | 与旧模板版本不一致（已自定义） | 智能 merge 提议（diff 语义合并），用户敲 |
| 新增 | 不存在 | 创建 |
| 新增 | 已存在 | 提议 merge / 全替，用户敲 |
| 删除 | 仍存在 | 提议删除（用户可保留） |

skipped[] 处理：
- 若文件在 skipped[] 中、且 `skipped_at_commit` 之后该文件**未变化** → 自动跳过、不进 TODO
- 若文件在 skipped[] 中、但之后**变化了** → 重新进 TODO（标注「上次 skip 是在 commit X，之后又改了」）

输出 TODO 清单（per-file 一条）：

```
TODO 同步清单：

[1] .pre-commit-config.yaml （root）
    模板侧：升级 ruff-pre-commit 到 v0.5.0
    项目侧：与旧版一致
    建议：take 新模板
    
[2] .gitignore （root）
    模板侧：新增 .ruff_cache/
    项目侧：手动加过 *.bak
    建议：智能 merge — 保留 *.bak、追加 .ruff_cache/
    
[3] .vscode/settings.json （subpath: .）
    模板侧：新增 source.organizeImports 配置
    项目侧：用户已自定义 editor.tabSize
    建议：段级 merge — 保留 tabSize、追加 organizeImports
    上次 skip 在 commit abc123，之后模板那条又改了
```

#### 4. Adopt 模式

- 列出可用 stacks
- AskUserQuestion 让用户选 stack
- 让用户选 path（单 stack 项目固定 `.`）
- 把模板的 `__root__/*` 和 `__subpath__/*`（path 应用于 subpath）当作"全是新增"列入 TODO（项目侧已有同名文件时仍逐条提议 merge，由 AI 智能判断）
- TODO 流程同 normal sync

#### 5. 用户批量决策

向用户呈现 TODO，让用户给出统一指令（如「全部 accept、第 3 条 skip、第 5 条改成全替」）。AI 解析后形成最终执行计划，再次回显让用户确认。

#### 6. 执行

- 对每个 accept 项：写文件 / 智能 merge 写回 / 删除文件
- 对每个 skip 项：在 marker 的 `stacks[0].skipped[]` 中追加 / 更新（带 `skipped_at_commit = HEAD`）
- 更新 marker 的 `template_commit = HEAD`、`bootstrap_time` 不动
- 不自动 commit，列出改动文件清单提示用户 review + 自行 commit

### Step 5：更新 `GLOBAL_CLAUDE.md`「项目本地推荐配置」段

把"建议每个项目都加"改成"通过 `/bootstrap` 选 stack 自动初始化、`/sync-project-config` 后续保持同步"。保留 `.prettierrc` / `.vscode/` 内容描述作为参考。

### Step 6：定义 `.cc-template.yml` schema 文档

写 `docs/11-跨项目共享模板与sync-skill/SCHEMA.md`，给出字段说明 + 单 stack / 多 stack 两种示例。让未来的人或 AI 一眼能看懂这个文件。

### Step 7：本仓库 dogfood

本仓库不是 python-uv 项目（是 bash + jq 配置仓库），不适合直接套 python-uv 模板。本轮 dogfood 仅限：

- 已有 `.prettierrc` 保留（不通过 templates 写入，因为本仓库非 stack 项目）
- 添加自己的 `.pre-commit-config.yaml`：用 `pre-commit-hooks` 的 `check-yaml` / `check-json` / `end-of-file-fixer` 等通用 hook（不属于任何 stack 模板，由仓库手动维护）—— **这一项可选，本轮可不做，留给后续**

### Step 8：提交策略

按全局 CLAUDE.md 流程：每个 step 自然成型后单独 commit；最后 SUMMARY.md 单独 commit。建议 commit 拆分：

- commit A: `feat(11): 新增 templates/python-uv/ 模板内容`
- commit B: `feat(11): install.sh 软链 templates 与 global-repo`
- commit C: `feat(11): 扩展 /bootstrap 支持 stack 选择与模板初始化`
- commit D: `feat(11): 新增 /sync-project-config skill（含 adopt 模式）`
- commit E: `docs(11): 更新 GLOBAL_CLAUDE.md 与新增 SCHEMA.md`
- commit F (最终): `docs(11): SUMMARY.md`

## 涉及文件

### 新增
- `templates/python-uv/__root__/.pre-commit-config.yaml`
- `templates/python-uv/__root__/.gitignore`
- `templates/python-uv/__root__/.github/workflows/lint.yml`
- `templates/python-uv/__root__/.prettierrc`
- `templates/python-uv/__subpath__/pyproject.toml.ruff.fragment`
- `templates/python-uv/__subpath__/.vscode/settings.json`
- `templates/python-uv/__subpath__/.vscode/extensions.json`
- `skills/sync-project-config/SKILL.md`
- `docs/11-跨项目共享模板与sync-skill/PLAN.md`（写入本计划副本）
- `docs/11-跨项目共享模板与sync-skill/SCHEMA.md`
- `docs/11-跨项目共享模板与sync-skill/SUMMARY.md`（最后写）

### 修改
- `install.sh`（增加两条 link_item 调用，main 流程）
- `skills/bootstrap/SKILL.md`（插入 Step 3.5 模板初始化、删除单独的 .prettierrc 写入）
- `GLOBAL_CLAUDE.md`（「项目本地推荐配置」段）
- `docs/DEVTREE.md`（轮次 11 节点；通过 `/devtree` skill 重建）

## 关键决策与复用要点

1. **复用 `link_item`**：install.sh 已有的软链 helper，新增两条不需要新逻辑
2. **复用 `merge_settings`**：本轮不需要修改 settings.base.json（templates 不走 hook 不登记到 settings）
3. **AI 直接读写 YAML**：不引入 yq / python-yaml 依赖，对齐 skills 的"AI 驱动"风格（参见 `/commit` skill 直接 AI 分析 lint 输出）
4. **smart merge 全交给 AI**：bootstrap 合并 pyproject.toml.ruff.fragment、sync 处理 user customization 都用 AI 阅读 + Edit/Write，不写 jq/sed merge 脚本（机械合并已被 PROMPT Q4 否决）
5. **skipped 持久化**：marker 中 skipped 项带 `skipped_at_commit`，sync 检测模板那条之后是否变了来决定是否重提
6. **多 stack 防误用**：sync 启动时显式 assert `len(stacks) == 1 and path == "."`，多 stack 直接报错退出（schema 已就位、逻辑此轮先不实现）

## 验证方式

### 1. install.sh 单元验证
```bash
bash install.sh
ls -la ~/.claude/templates ~/.claude/global-repo
# 期望：两条 symlink 都存在并指向本仓库
```

### 2. bootstrap 端到端
```bash
mkdir /tmp/test-bootstrap && cd /tmp/test-bootstrap
git init
# 在 CC 中跑 /bootstrap，选 python-uv stack
ls -la
# 期望：CLAUDE.md, README.md, DEVTREE.md, .pre-commit-config.yaml, .gitignore,
#       .prettierrc, .github/workflows/lint.yml, .vscode/, .cc-template.yml
cat .cc-template.yml
# 期望：source / template_commit / bootstrap_time / stacks[0].stack=python-uv / path=.
```

### 3. pre-commit 实测
```bash
cd /tmp/test-bootstrap
uv init  # 让 pyproject.toml 存在
# 在 CC 中再跑一次 /sync-project-config，把 ruff fragment 合并进 pyproject.toml
uv add --dev pre-commit
uv run pre-commit install
uv run pre-commit run --all-files
# 期望：无报错通过
```

### 4. sync 正常路径
```bash
# 在 claude-code-global 仓库中改 templates/python-uv/__root__/.gitignore 加一行 *.swp
git commit -am "test: add swp to gitignore template"
# 切回 /tmp/test-bootstrap
cd /tmp/test-bootstrap
# 在 CC 中跑 /sync-project-config
# 期望：TODO 列出 .gitignore 一条，accept 后项目侧 .gitignore 出现 *.swp，
#       .cc-template.yml 中 template_commit 推进
```

### 5. sync adopt 路径
```bash
mkdir /tmp/test-adopt && cd /tmp/test-adopt
git init
echo "# Hello" > README.md
git add . && git commit -m "init"
# 在 CC 中跑 /sync-project-config
# 期望：进入 adopt 模式 → 询问 stack → 写入完整模板 + .cc-template.yml
```

### 6. skipped 持久化
```bash
# 在 sync TODO 中 skip .prettierrc，确认 .cc-template.yml.skipped[] 多了一条带 skipped_at_commit
# 第二次跑 sync，模板未变化 → .prettierrc 不再进 TODO
# 改 templates/python-uv/__root__/.prettierrc，commit
# 第三次跑 sync → .prettierrc 重新进 TODO
```

### 7. 多 stack 防误用
```bash
# 手动改 .cc-template.yml 加第二个 stack
# 跑 /sync-project-config
# 期望：明确报错「本轮仅支持单 stack，多 stack 留下一轮」并退出
```

## 风险与边界

- **bootstrap 改动较大**（之前只是 5 步骨架，现在要做模板分发），可能影响已经依赖 bootstrap 的人。但本仓库目前只是个人项目，破坏性可接受
- **YAML 由 AI 解析**有误读风险（rare），但 marker 字段简单 + skill 在写之前会自我回显让用户确认，可控
- **smart merge 由 AI 决策**，可能在复杂 merge 场景给出不理想结果。已通过"用户批量决策 + 显式确认"作为防线
- **未在 ~/.claude/global-repo 这条 symlink 上做循环检测**。理论上若用户的仓库 clone 在 `~/.claude/` 里会形成自指，实际不可能；不做防御
