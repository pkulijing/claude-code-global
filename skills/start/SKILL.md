---
name: start
description: 开始一个新的开发项：创建文档目录，撰写 PROMPT.md 和 PLAN.md，确认后再开始写代码
disable-model-invocation: true
---

用户调用此 skill 表示要开始一个新的开发项。

**前置检查**：若 `CLAUDE.md` 与 `DEVTREE.md` 都不存在，停下来提示用户先运行 `/bootstrap`，**不要**自己兜底建项目骨架。`/start` 只负责开新一轮开发，不负责项目首次初始化。

**参数处理**：调用时可能附带参数（args），参数有两种形态：

- **issue 驱动**（推荐）：参数是 `#<数字>` 或完整 issue URL：
  - GitHub: `https://github.com/owner/repo/issues/N`
  - GitLab: `https://gitlab.com/<namespace>/<project>/-/issues/N`（自托管把 host 换为对应实例域名）
  - 走「issue 驱动分支」（见下文）
- **自由描述**：参数是对需求的自由文字描述
  - 走「自由描述分支」（与原流程一致）

无参数 → 追问用户本次开发项的需求是什么或对应的 issue 号，拿到后再继续。

按照全局 CLAUDE.md 中的开发模式，严格遵循「执行前必须先完成 PROMPT.md 和 PLAN.md 的撰写并确认，再开始写代码」：

### 通用流程

1. 在 `docs/` 下创建新的开发项文件夹（数字递增 + 中文描述；issue 驱动时从 issue 标题提炼简短中文描述）
2. 基于参数撰写 `PROMPT.md`（两个分支具体行为见下）
3. 进入计划模式，撰写 `PLAN.md` 并请用户确认
4. 用户确认后再开始写代码

### issue 驱动分支

参数命中 `#数字` 或上述任一平台的 issue URL 时：

1. **拉 issue 详情**：调 helper（自动按 `git remote get-url origin` 走 GitHub 或 GitLab）：

   ```bash
   python3 $HOME/.claude/scripts/platform_issue.py issue-view <N>
   ```

   如参数是完整 URL，先从中提取 N。helper stdout 输出归一 json（GitHub 风格字段），schema 固定为：

   ```json
   {
     "number": 3,
     "title": "...",
     "body": "...",
     "url": "https://...",
     "labels": ["type:X", "area:Y", "priority:Z"]
   }
   ```

   GitLab 端的 `iid` / `web_url` / `description` 已在 helper 内归一为 `number` / `url` / `body`，本 SKILL 直接按上述 schema 读字段。

2. **PROMPT.md 顶部**写一段引用块（让未来的人或 AI 一眼看到来源）：

   ```markdown
   > 来自 [#<N> <issue 标题>](<issue URL>)
   > Labels: `type:X` `area:Y` `priority:Z`
   ```

3. **PROMPT.md 主体**：把 issue body 内容作为「背景 / 需求」段的起点，AI 据此扩写完整的 PROMPT.md（可能基于 issue body 增补：约束、范围、待决问题等）。如 issue body 已足够完整，直接复用为主要内容。
4. 文件夹命名：从 issue 标题提炼简短中文描述，规则：`docs/<编号>-<中文描述>/`

### 自由描述分支

参数是文字描述时（非 issue 引用）：流程同原版。AI 基于参数撰写 PROMPT.md，文件夹命名从描述提炼。

> 提示：自由描述分支适合「轻量改动 / 探索性 round / 不需要长期追踪的开发项」。**长期可追踪的开发项推荐先 `/backlog` 创 issue，再 `/start <issue#>`**。
