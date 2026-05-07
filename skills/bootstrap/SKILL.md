---
name: bootstrap
description: 为空项目搭建文档骨架（README.md / CLAUDE.md / DEVTREE.md），仅在项目首次开发前调用一次
disable-model-invocation: true
---

用户调用此 skill 表示要为一个**全新空项目**搭建文档骨架。本 skill 是一次性脚手架，**不**用于已有 `docs/` 历史的项目。

## 前置检查

按顺序检查，**任一命中就立即停止并报告**，不要尝试覆盖已有内容：

- `docs/` 下已存在 `N-` 数字前缀开头的开发轮次目录 → "项目已初始化（检测到 docs/N-xxx），不应运行 bootstrap。"
- `CLAUDE.md` 已存在 → "已有 CLAUDE.md，如要重置请先备份再删除原文件。"
- `DEVTREE.md` 已存在 → 同上提示

全部通过才继续。

## 信息收集

**一次性问全**，不要逐条来回：

1. **项目名称**（默认取当前目录名，告知默认值）
2. **项目一句话描述**（用作 README 与 CLAUDE.md 的开篇）
3. **是否已有第一个待启动开发项的初步想法？**（仅用于决定收尾时是否提示运行 `/backlog`，不需要详细内容）

参数（args）若非空，可作为问题 1 或 2 的输入；不足部分仍需向用户问全。

## 执行流程

### Step 1：写 README.md

```markdown
# {项目名}

{一句话描述}

## 目录结构

（待补充）

## 开发流程

本项目遵循 [全局 Constitution](~/.claude/CLAUDE.md) 中定义的「需求 - 计划 - 执行 - 总结」四步开发模式，文档记录见 `docs/`。
```

### Step 2：写 CLAUDE.md

```markdown
# {项目名}

{一句话描述}

## 目录结构

（待补充）

## 开发注意事项

（待补充）
```

**不**调用内置 `/init`：空项目无可扫的代码，等代码长起来后由用户手动跑 `/init` 重写更合适。

### Step 3：模板初始化（\_common + 按 stack）

为项目套用一份与 `claude-code-global` 仓库管理的"跨项目共享开发配置"，包含 `.pre-commit-config.yaml` / `.vscode/` / `.gitignore` / `lint.yml` / `.gitlab-ci.yml` / `pyproject.toml [tool.ruff]` / `.github/ISSUE_TEMPLATE/` / `.gitlab/issue_templates/` / `.github/labels.yml` / `.prettierrc` 等。**GitHub 与 GitLab 双轨同时落**（互不干扰：GitHub Actions 不读 `.gitlab-ci.yml`、GitLab CI 不读 `.github/workflows/`，issue templates 同理），skill 中实际调命令行的步骤（如 `gh label create`）按当前 `git remote` 判定走哪一支。详细字段约定见 `~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/SCHEMA.md`。

`~/.claude/templates/` 下有两类目录：

- **`_common/`**：所有项目都套用，stack-无关（issue templates 双套、labels.yml、.prettierrc 等通用资源），bootstrap 会**自动应用**，不让用户选择
- **`<stack>/`**（如 `python-uv`）：技术栈特异资源，由用户选择套用其中之一

#### Step 3.1：探测可用 stack

- 读取 `~/.claude/templates/` 下**非下划线开头**的子目录，得到可选 stack 列表（如 `python-uv`）
- 下划线开头的目录（如 `_common/`）是伪 stack，自动应用，不进入用户选项
- `~/.claude/templates/` 不存在 → 提示用户「尚未通过 install.sh 部署 templates，跳过模板初始化」并跳过 Step 3 整个段落

#### Step 3.2：用户选 stack

用 `AskUserQuestion` 让用户在以下选项中选一个：

- 各 stack 名（每个 stack 一个选项）
- 「跳过模板初始化（不推荐，但允许）」

若选「跳过」→ 跳过 Step 3.3，但 **`_common` 仍然应用**（除非 `_common/` 也不存在）；若 `_common/` 不存在则 Step 3.3 完全跳过。

#### Step 3.3：复制模板内容到项目

设单 stack 项目 `path = .`。**先应用 `_common`，再应用用户选的 `<stack>`**（同名文件以 `<stack>` 优先，但理论上不应有冲突 —— 见 `~/.claude/global-repo/docs/12-backlog改为issue驱动/SUMMARY.md` 中 \_common 与 stack 的边界划分）。

对每个生效目录（先 `_common/` 后 `<stack>/`）：

- 把 `__root__/` 下所有文件（含点文件、含子目录结构）复制到项目根
- 把 `__subpath__/` 下所有文件复制到项目根（path 即 `.`）
- 遇到目标已存在的文件：列入「冲突清单」，逐条向用户确认 take 模板 / 保留项目侧 / 智能合并；不要默认覆盖

特殊处理：

- `pyproject.toml.ruff.fragment` 不能直接落地为同名文件 —— 它是片段，需合并进项目根的 `pyproject.toml` 的 `[tool.ruff]` 段
  - 项目根**没有** `pyproject.toml` → 提示用户先 `uv init` 后再运行 `/sync-project-config` 单独合并 ruff 段
  - 项目根**有** `pyproject.toml` → 用 AI 智能合并：保留用户已有的字段，追加片段缺的；冲突字段询问用户

#### Step 3.3.5：同步 labels（按 origin 平台判定）

复制完后，如果项目根出现了 `.github/labels.yml`（来自 `_common`），按 `git remote get-url origin` 的输出分支处理：

- origin 含 `github.com` → **跑 GitHub label 同步**：
  - 解析 `.github/labels.yml`（YAML list of `{name, color, description}`）
  - 对每条调 `gh label create --force "<name>" --color "<color>" --description "<desc>"`（`--force` 在 gh ≥ 2.40 是更新已存在；旧版用 `|| true` 容错）
- origin 含 `gitlab` 字样（含自托管时 URL 含 `gitlab` 字样）→ **跳过**，打印「检测到 GitLab remote，labels 同步将在后续 `gh→glab` 适配 issue 落地，本轮请手动维护或暂缓」
- 其他（无 origin / 自托管 GitLab URL 不含 `gitlab` 字样 / 未知平台）→ **跳过**，打印「无法从 origin 判定平台，labels 同步跳过；如确为 GitHub 请补 origin 后跑 `/sync-project-config`，如为 GitLab 暂留待后续 issue 落地」

本轮**不**调 `glab label create`（GitLab labels 同步整体留给后续 issue）。

#### Step 3.4：写 `.cc-template.yml` marker

在项目根创建 `.cc-template.yml`，内容如下（字段来源详见 SCHEMA.md）：

```yaml
# 由 claude-code-global 管理，非必要请勿手动编辑
source: <git -C ~/.claude/global-repo config --get remote.origin.url 的输出>
template_commit: <git -C ~/.claude/global-repo rev-parse HEAD 的输出>
bootstrap_time: <当前 UTC 时间的 ISO 8601 字符串>
stacks:
  - stack: <用户选的 stack 名>
    path: .
    skipped: []
```

`source` 取不到 origin 时填占位符 `https://github.com/<owner>/claude-code-global`，并在收尾里提示用户手动补全。

### Step 4：调用 `/devtree` 落 DEVTREE.md 骨架

直接调用 `/devtree`。`/devtree` 自身已支持「冷启动」：当 `docs/DEVTREE.md` 不存在或 Epic 结构为空时，会写入完整骨架（分类图例 + 可视化占位 + 节点索引占位 + Epic 结构占位）。

**不要**在本 skill 里复制一份 DEVTREE 骨架模板 —— 单一事实来源在 `/devtree`。

### Step 5：收尾反馈

- echo-back 新建文件的路径：`README.md`、`CLAUDE.md`、`docs/DEVTREE.md`，以及（若 Step 3 未跳过）模板复制的文件清单 + `.cc-template.yml`（跳过的项注明「已存在，未覆盖」或「用户在冲突清单中选择保留」）
- 给出下一步建议清单：
  1. 检查并补完 `README.md` 与 `CLAUDE.md` 的「待补充」段
  2. 在 `DEVTREE.md` 的「Epic 结构」区块下添加首批叶 Epic
  3. 若 Step 3 已套用 stack 模板：进项目跑 `pre-commit install` 启用 commit 闸门
  4. 若 Step 3 跳过 / `pyproject.toml` 不存在：未来可运行 `/sync-project-config` 走 adopt 模式补全
  5. 若 Step 3.3.5 跳过了 labels 同步：
     - origin 是 GitHub 但 `gh auth` 失败：提示「跑 `gh auth login` 后再 `/sync-project-config`」
     - 无 origin：提示「先 `gh repo create` / `glab repo create` 关联 remote，再跑 `/sync-project-config` 把 labels 推上去（GitHub 自动；GitLab 暂留待后续 issue）」
     - origin 是 GitLab：提示「GitLab labels 同步将在后续 `gh→glab` 适配 issue 落地，可关注 #2 的关联 issue」
  6. 若 `.github/labels.yml` 中 `area:` 段还是占位符：提示「按本项目实际模块改 area 段后（GitHub 项目）再跑 Step 3.3.5 等价的 `gh label create` 同步」
  7. 若已有第一个开发项想法（信息收集第 3 问回答「有」），运行 `/backlog` 登记
  8. 准备好后运行 `/start` 开启 round 0
- **不调用 `/commit`** —— 是否立即提交由用户决定（与 `/backlog` 一致）
