---
name: backlog
description: 把一条 backlog 创建成 issue（GitHub / GitLab 自动双轨，含三轴 label）+ 在 docs/BACKLOG.md 索引中加一行链接
disable-model-invocation: false
---

用户调用此 skill 表示要新增一条 backlog。本仓库工作流：**issue 是真源**（详情、讨论、跨轮上下文都沉淀在 issue 里），`docs/BACKLOG.md` 退化为「未关闭 issue 的扁平索引」。本 skill 完成两件事：

1. 走 issue template 创建一个 issue（含三轴 label）—— 平台由 `git remote get-url origin` 自动判定 GitHub / GitLab
2. 在 `docs/BACKLOG.md` 对应 priority 段加一行链接

删除职责仍在 `/finish` 里（commit 含 `Closes #N` → 自动关 issue + 删 BACKLOG.md 那行；`Closes #N` 在 GitHub / GitLab 默认分支均自动关 issue）。

所有平台耦合的 CLI 调用都通过 helper `python3 $HOME/.claude/scripts/platform_issue.py <subcommand>`，本 SKILL 不直接调 `gh` / `glab`。

## 前置检查

按顺序，**任一失败立即停止并报告**：

- `git rev-parse --is-inside-work-tree` → 必须是 git 仓库
- `python3 $HOME/.claude/scripts/platform_issue.py detect-platform` → exit 0 表示已识别 GitHub / GitLab；exit 2 表示无法判定平台（提示用户配 origin remote 或用 `--platform <p>` override）
- `python3 $HOME/.claude/scripts/platform_issue.py auth-status` → 对应平台 CLI 必须已登录（exit 3 提示用户跑 `gh auth login` 或 `glab auth login`；exit 4 提示安装对应 CLI）
- `.github/ISSUE_TEMPLATE/feat.md` 等模板存在 → 否则提示「先 `/sync-project-config` 同步模板」（round 14 后两端模板共存于同一项目，本检查项目侧均适用）

## 参数处理

- **有参数**：参数是这条 backlog 的原始描述（一句话或半结构化）
- **无参数**：追问「本次要加的 backlog 条目是什么？」

## 执行流程

### Step 1：选 issue 类型

`AskUserQuestion`：让用户选 `feat` / `bug` / `spike` 之一。决定走哪份模板。

### Step 2：协作填 body

读对应模板（`.github/ISSUE_TEMPLATE/<type>.md`）。基于其骨架字段（如 feat 模板的「动机 / 希望达到 / 候选方向 / 风险 / scope」），AI 按字段引导用户填：

- 信息够：直接基于参数 + 用户对话内容生成
- 信息不够：写「待补充」，**不脑补**
- 用户明示「先放着之后再补」：尊重，body 写最少必要字段

对话来回 **1~2 轮够了**，不要拖。

### Step 3：选 area

读 `.github/labels.yml`（或缺失时 `python3 $HOME/.claude/scripts/platform_issue.py label-list` 取 fallback）拿 `area:*` 列表。labels.yml 在 GitLab 项目下也读 `.github/` 路径 —— round 15 后该文件 schema 跨平台共用，是 helper 私有输入而非平台读的死文件。

`AskUserQuestion`：让用户从 area 列表中选一条。如列表为空（仅 placeholder），允许用户输入新 area 名（warn 一句「这个 area 不在 labels.yml 中，建议本轮结束后补到 labels.yml + 跑 `/sync-project-config` 同步到远端 labels」）。

### Step 4：选 priority

`AskUserQuestion`：选 `P0` / `P1` / `P2`，并要求**一句话说明优先级判断理由**（写到 issue body 顶部 blockquote 中）。

### Step 5：回显草稿 + 三轴 label

把 title + body + 三个 label 一并展示，等用户确认。允许调整任意字段，**不自动落盘**。

### Step 6：执行 —— 创建 issue + 加 BACKLOG 索引

#### 6.1 创建 issue

把 Step 5 确认过的 body 内容写到临时文件 `/tmp/backlog-body.md`（用 Write 工具），再调 helper：

```bash
python3 $HOME/.claude/scripts/platform_issue.py issue-create \
  --title "<标题>" \
  --body-file /tmp/backlog-body.md \
  --label "type:<X>" \
  --label "area:<Y>" \
  --label "priority:<Z>"
```

helper stdout 输出新建 issue 的 URL（单行），从中提取 issue 号 `#N`。GitHub URL pattern: `.../issues/N`；GitLab URL pattern: `.../-/issues/N`。

#### 6.2 BACKLOG.md 不存在 → 用新骨架初始化

新骨架（`{slug}` 由 `python3 $HOME/.claude/scripts/platform_issue.py repo-slug` 获取 —— GitHub 端为 `owner/repo`，GitLab 端为 `namespace/project`；`{项目名}` 默认取 git 仓库名；`{closed-issues-url}` 按 `detect-platform` 输出生成：GitHub 用 `https://github.com/{slug}/issues?q=is%3Aissue+is%3Aclosed+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2`，GitLab 用 `https://gitlab.com/{slug}/-/issues?state=closed&label_name[]=priority:P0&label_name[]=priority:P1&label_name[]=priority:P2`，自托管 GitLab 把 host 替换为对应实例域名）：

```markdown
# {项目名} — Backlog

未来开发项的**速览索引**。每条都对应一个 issue（GitHub / GitLab 自动判定），**详情、讨论、跨轮上下文都在 issue 里**。

**为什么这样组织**：issue 是真源（permanent history + 通过 `Closes #N` 跟 commit/PR 永久关联，开发完归档进 closed 仍可检索）。这个文件是当前还没开发的项的扁平快照，方便一眼扫到全图、决定下一轮挑哪个。

## 工作流

- **新增想法** → `/backlog` 走 issue templates，挂三轴 label，建完顺手在本文件相应分组里加一行
- **开新轮** → 从下面挑一条 → `/start <issue#>` 把 issue 详情贴进 PROMPT.md → 开干
- **收尾一轮** → PR / commit message 写 `Closes #<issue 号>` 自动关 issue → `/finish` 删本文件这一行

## 三轴分类约定

- **type**：`type:feat` / `type:bug` / `type:refactor` / `type:perf` / `type:test` / `type:docs`
- **area**：模块分类，按本项目 `.github/labels.yml` 中的 `area:*` 列表
- **priority**：`P0`（必须做、不做有重大风险）/ `P1`（重大新功能 / 用户能感知的明显问题）/ `P2`（一般小功能 / 偶发问题 / 触发面窄）

## P0 — 必须做

(暂无)

## P1 — 重大新功能

(暂无)

## P2 — 一般小功能小修复

(暂无)

## 已完成 / 不再追踪

历史已完成项**不在本文件追踪**，直接看 [closed issues with priority labels]({closed-issues-url})。

下面只列**刻意决定不做**的条目（避免未来翻老 SUMMARY 误以为是遗漏）：

(暂无)
```

#### 6.3 在对应 priority 段追加一行

行格式：

```
- [#N <标题>](URL) · `type:X` `area:Y` —— <一句话理由（来自 priority 判断）>
```

定位策略：

- priority 是 P0 → 在 `## P0 — 必须做` 段最后一条之后追加
- priority 是 P1 → 在 `## P1 — 重大新功能` 段最后一条之后追加
- priority 是 P2 → 在 `## P2 — 一般小功能小修复` 段最后一条之后追加
- 如果该段当前是 `(暂无)`，把 `(暂无)` 替换成新条目（不再保留 `(暂无)`）

### Step 7：反馈

打印新创建的 issue URL + BACKLOG.md 中追加的位置，让用户确认。

**不调用 `/commit`** —— 是否立刻 commit BACKLOG.md 改动由用户决定。
