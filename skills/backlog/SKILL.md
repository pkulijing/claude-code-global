---
name: backlog
description: 把一条 backlog 创建成 issue（GitHub / GitLab 自动双轨，含三轴 label）—— issue 即单一真源，无本地索引文件
disable-model-invocation: false
---

用户调用此 skill 表示要新增一条 backlog。本仓库工作流：**issue 是单一真源**（详情、讨论、跨轮上下文都沉淀在 issue 里），**无本地索引文件**——「未关闭 open 项速览」由一个按 priority label 过滤 open issues 的 saved query 承担（README / GLOBAL_AGENTS.md 挂链接）。本 skill 只做一件事：

- 走 issue template 创建一个 issue（含三轴 label）—— 平台由 `git remote get-url origin` 自动判定 GitHub / GitLab

issue 关闭仍由 `/finish` 完成（commit 含 `Closes #N` → 合并到 default branch 自动关 issue；`Closes #N` 在 GitHub / GitLab 均原生生效）。

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

询问用户，让其在 `feat` / `bug` / `spike` 中选一个。决定走哪份模板。

### Step 2：协作填 body

读对应模板（`.github/ISSUE_TEMPLATE/<type>.md`）。基于其骨架字段（如 feat 模板的「动机 / 希望达到 / 候选方向 / 风险 / scope」），AI 按字段引导用户填：

- 信息够：直接基于参数 + 用户对话内容生成
- 信息不够：写「待补充」，**不脑补**
- 用户明示「先放着之后再补」：尊重，body 写最少必要字段

对话来回 **1~2 轮够了**，不要拖。

### Step 3：选 area

读 `.github/labels.yml`（或缺失时 `python3 $HOME/.claude/scripts/platform_issue.py label-list` 取 fallback）拿 `area:*` 列表。labels.yml 在 GitLab 项目下也读 `.github/` 路径 —— round 15 后该文件 schema 跨平台共用，是 helper 私有输入而非平台读的死文件。

询问用户，让其从 area 列表中选一条。如列表为空（仅 placeholder），允许用户输入新 area 名（warn 一句「这个 area 不在 labels.yml 中，建议本轮结束后补到 labels.yml + 跑 `/sync-project-config` 同步到远端 labels」）。

### Step 4：选 priority

询问用户，让其在 `P0` / `P1` / `P2` 中选一个，并要求**一句话说明优先级判断理由**（写到 issue body 顶部 blockquote 中）。

### Step 5：回显草稿 + 三轴 label

把 title + body + 三个 label 一并展示，等用户确认。允许调整任意字段，**不自动落盘**。

### Step 6：执行 —— 创建 issue

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

**不再有任何本地索引写入**——issue 建成即已进入云端真源，open 项速览由 saved query（见 Step 7）承担。

### Step 7：反馈

打印新创建的 issue URL，让用户确认。再附一行「open 项速览」的 saved query 链接（按 priority 过滤未关闭 issue），方便用户挑下一轮：

- GitHub：`https://github.com/{slug}/issues?q=is%3Aissue+is%3Aopen+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2`
- GitLab：`https://gitlab.com/{slug}/-/issues?state=opened&label_name[]=priority:P0&label_name[]=priority:P1&label_name[]=priority:P2`（自托管把 host 换成对应实例域名）

`{slug}` 由 `python3 $HOME/.claude/scripts/platform_issue.py repo-slug` 获取（GitHub 端 `owner/repo`，GitLab 端 `namespace/project`）。

**不调用 `/commit`** —— 本 skill 只动云端 issue、不改任何本地文件，无需 commit。
