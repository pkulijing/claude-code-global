---
name: bootstrap
description: 为空项目搭建文档骨架（README.md / CLAUDE.md / DEVTREE.md），仅在项目首次开发前调用一次
disable-model-invocation: false
---

用户调用此 skill 表示要为一个**全新空项目**搭建文档骨架。一次性脚手架，**不**用于已有 `docs/` 历史的项目 —— 那种走 `/sync-project-config` 的 adopt 模式。

## 前置检查

命中任一就立即停止并报告，**不要尝试覆盖已有内容**：

- `docs/` 下已有 `N-` 数字前缀的开发轮次目录 → 「项目已初始化（检测到 docs/N-xxx），不应运行 bootstrap。」
- `CLAUDE.md` 或 `DEVTREE.md` 已存在 → 「已有 X，如要重置请先备份再删除原文件。」

## 信息收集

**一次性问全**，不要逐条来回：

1. **项目名称**（默认取当前目录名，告知默认值）
2. **项目一句话描述**（用作 README 与 CLAUDE.md 的开篇）
3. **是否已有第一个待启动开发项的初步想法？**（仅用于决定收尾是否提示 `/backlog`）

args 非空时可作为问题 1 或 2 的输入；不足部分仍需问全。

## Step 1 · 写 README.md

```markdown
# {项目名}

{一句话描述}

## 目录结构

（待补充）

## 开发流程

本项目遵循 [全局 Constitution](https://github.com/pkulijing/claude-code-global/blob/master/GLOBAL_AGENTS.md) 中定义的「需求 - 计划 - 执行 - 总结」四步开发模式，文档记录见 `docs/`。
```

## Step 2 · 写 CLAUDE.md

同样的 `# {项目名}` + 描述开头，加「## 目录结构」「## 开发注意事项」两个「（待补充）」段。

**不**调用内置 `/init`：空项目无可扫的代码，等代码长起来后由用户手动跑更合适。

## Step 3 · 模板初始化

为项目套用一份 `claude-code-global` 管理的跨项目共享开发配置（`.pre-commit-config.yaml` / `.vscode/` / `.gitignore` / CI / `pyproject.toml` 各段 / issue templates 双套 / `.github/labels.yml` / `.prettierrc` 等）。**GitHub 与 GitLab 双轨同时落**、互不干扰（各读各的 CI 与 issue templates）。

`~/.claude/templates/` 不存在 → 提示「尚未通过 install.sh 部署 templates，跳过模板初始化」并跳过整个 Step 3。

### 3.1 探测可用 stack

读 `~/.claude/templates/` 下**非下划线开头**的子目录得可选 stack；对每个读其 `stack.yml` 取 `default_path` 与 `label`。落点规则与 `_common` 的地位见 `templates/MECHANICS.md` §1。

### 3.2 用户选 stack（可多选）

前端 / 后端正交，可叠加。让用户**勾选 0 个或多个**，各选项展示其 `label`。**不向用户询问 path** —— 由各 stack 的 `default_path` 决定。一个都不选则只应用 `_common`。

### 3.3 复制模板内容到项目

**动手前先读 `templates/MECHANICS.md`** —— 落点语义、fragment 合并、变体组落地、迁移去重全在那里，本 skill 不复述。

顺序：先 `_common`，再按用户选的每个 `<stack>` 依次应用。对每个来源把 `__root__/` 与 `__subpath__/` 下所有文件（含点文件与子目录）复制到各自落点，目标已存在的列入冲突清单逐条确认。

**`*.fragment` 与 `<target>.variant.<key>` 两类文件要从普通复制流程中剔除**，不落地为同名文件 —— 它们分别走 3.3.6 的选一个落地与 3.3.7 的合并（**变体先落地、fragment 后合并**，理由见 3.3.7）。

### 3.3.5 同步 labels

项目根出现 `.github/labels.yml`（来自 `_common`）时调 helper：

```bash
python3 $HOME/.claude/scripts/platform_issue.py label-sync-from-file .github/labels.yml
```

stdout 原样展示给用户；exit 2/3/4 按契约降级为收尾提示（Step 5 第 6 条），不阻塞后续。helper 完整行为见 `~/.claude/scripts/platform_issue.md`。

### 3.3.6 落地变体组

对 3.3 按 `<target>` 聚合出来的每个变体组，按 `templates/MECHANICS.md` §3 问用户选一个 key 并只落地那一份，**记住每个组的选择**供 3.6 写进 marker。

### 3.3.7 合并 fragments

对 3.3 剔除出来的每一份 `*.fragment`，按 `templates/MECHANICS.md` §2 合并。单包 `python-uv` 且项目根无 `pyproject.toml` 时，相关片段标记 **needs-step-3.5**，等 3.5 生成骨架后回到本步再合。

> **这一步必须排在 3.3.6 之后，顺序不许调换** —— 理由见 `templates/MECHANICS.md` §2.3 硬约束 1。

### 3.5 后端可跑化（选中含 `python-uv` 或 `python-uv-workspace` 时）

按 `templates/MECHANICS.md` §4 执行四步（确保 `pyproject.toml` → 装 dev 依赖 → 确保 pre-commit → 注册 git hook）。生成骨架后**回到 3.3.7** 处理所有标记 needs-step-3.5 的片段。都没选中则整段跳过。

### 3.5b 前端依赖安装（选中含 `react-vite` 时）

按 `templates/MECHANICS.md` §5 执行。没选中则整段跳过。

### 3.6 写 `.agent-template.yml` marker

在项目根创建（字段来源详见 `~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/SCHEMA.md`）：

```yaml
# 由 claude-code-global 管理，非必要请勿手动编辑
source: <git -C ~/.claude/global-repo config --get remote.origin.url 的输出>
template_commit: <git -C ~/.claude/global-repo rev-parse HEAD 的输出>
bootstrap_time: <当前 UTC 时间的 ISO 8601 字符串>
stacks:
  - stack: python-uv
    path: .
    skipped: []
    variants: # 仅当该 stack 落了变体组时写，缺省不写
      .gitlab-ci.yml: shell # 3.3.6 用户选的 key
  - stack: react-vite
    path: frontend
    skipped: []
```

上例是「后端 + 前端」并存形态；只选其一就只写那一条；一个都没选则写 `stacks: []` 并在**顶层**加 `skipped: []`。`source` 取不到 origin 时填占位符 `https://github.com/<owner>/claude-code-global`，并在收尾提示用户补全。

## Step 4 · 调用 `/devtree` 落 DEVTREE.md 骨架

直接调用 `/devtree` —— 它自身已支持冷启动，`docs/DEVTREE.md` 不存在或 Epic 结构为空时会写入完整骨架。**不要**在本 skill 里复制一份骨架模板，单一真源在 `/devtree`。

## Step 5 · 收尾反馈

echo-back 新建文件的路径（`README.md`、`CLAUDE.md`、`docs/DEVTREE.md`，以及 Step 3 未跳过时的模板文件清单 + `.agent-template.yml`），跳过的项注明原因。然后给下一步建议：

1. 补完 `README.md` 与 `CLAUDE.md` 的「待补充」段
2. 在 `DEVTREE.md` 的「Epic 结构」区块下添加首批叶 Epic
3. 已跑 3.5 的：项目已可 `uv run pytest` / `git commit`，可选跑 `pre-commit run --all-files` 验证（首次接入易出 finding）。已跑 3.5b 的：`frontend/` 已可 `npm run dev` / `npm run build`
4. 3.5 被用户跳过的：未来可手动跑 `uv init --package && uv add --dev pytest pytest-cov ruff && uv tool install pre-commit && pre-commit install`，或重跑 `/sync-project-config` 走 adopt
5. Step 3 整段跳过 / 选了非 python stack 的：未来可运行 `/sync-project-config` 走 adopt 补全
6. 3.3.5 跳过了 labels 同步的：按 `scripts/platform_issue.md`「exit code 降级」表逐码补救，补齐后重跑 `/sync-project-config`
7. `.github/labels.yml` 的 `area:` 段还是占位符的：按本项目实际模块改完再 `/sync-project-config` 重新同步
8. 已有第一个开发项想法的：运行 `/backlog` 登记
9. 准备好后运行 `/start` 开启 round 0
10. 领域规范集中在 `~/.claude/playbooks/`、按 GLOBAL_AGENTS 的触发条件主动读入，**不需要在项目根另放指针 md**

**不调用 `/commit`** —— 是否立即提交由用户决定（与 `/backlog`、`/sync-project-config` 一致）。
