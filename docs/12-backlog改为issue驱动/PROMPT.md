# PROMPT：backlog 工作流改造为 GitHub Issue 驱动

## 背景

当前 `claude-code-global` 中的 backlog 工作流由 `/backlog` skill 管理：

- 用户调用 `/backlog`，AI 帮忙扩写出 5 字段结构化条目（动机 / 目标状态 / 候选方向 / 风险 / scope），写入项目 `docs/BACKLOG.md`
- `/finish` 收尾时如果本轮来自某个 backlog 条目，从 `BACKLOG.md` 删掉它
- BACKLOG.md 是「权威来源」，负责跨轮追踪职责

**当前模型的问题**（在 `daobidao`（即 `whisper-input`）项目实际运行 30+ 轮后浮现的）：

1. **跨轮上下文沉淀在文件里、和 git/PR 脱节**：BACKLOG 条目里讨论"候选方向 A vs B"，但实际 commit 信息与 PR 描述里也在讨论同一件事，**两份内容不互通**，未来读 git log 看不到决策上下文
2. **完成后只是"删一行"，历史记忆丢失**：删除是为避免文件腐烂，但代价是"为什么没做这条 / 为什么改了这个方案" 的判断过程消失
3. **没有原生工具可索引**：BACKLOG.md 是裸文本，没法 label / 没法 query / 没法跨项目对比，全靠肉眼扫
4. **新想法在 SUMMARY.md「后续 TODO」段腐烂**：每轮结尾的 TODO 段没有强制流入 BACKLOG，作者经常半年后翻老 SUMMARY 才想起来

## 目标

把 backlog 工作流改造为**以 GitHub Issue 为真源**的模型，参考 `daobidao` 项目已落地一段时间、稳定运行的做法（[whisper-input/docs/BACKLOG.md](/Users/jing/Developer/whisper-input/docs/BACKLOG.md) + [whisper-input/.github/ISSUE_TEMPLATE/](/Users/jing/Developer/whisper-input/.github/ISSUE_TEMPLATE/)）。

核心心智模型：

| 角色 | 旧 | 新 |
|---|---|---|
| 真源 / 详情 / 历史 | `docs/BACKLOG.md` | **GitHub Issues**（permanent，含 closed） |
| `docs/BACKLOG.md` | 5 字段结构化条目 | **扁平索引**：每条一行，含 issue 链接 + 三轴 label 摘要 |
| 新增想法 | `/backlog` 写入 BACKLOG.md | `gh issue create` 走 issue template |
| 关闭追踪 | `/finish` 删 BACKLOG.md 一行 | commit/PR 写 `Closes #N` 自动关 issue + 删 BACKLOG.md 那一行 |
| 跨轮上下文 | 散在 BACKLOG.md / SUMMARY.md「后续 TODO」 | issue 评论区 + commit message + PR description |

让"为什么这样做"的判断过程**永久沉淀在 issue 里**，与 git history 双向链接；让 BACKLOG.md 变成一眼可扫的"待选清单"，腐烂成本低。

## 改革要点（从 daobidao 实践提炼）

### 1. 三轴 Label 体系

每条 issue 必须打三个 label：

- `type:*`：`feat` 新功能 / `bug` bug 修复 / `refactor` 重构 / `perf` 性能 / `test` 测试基建 / `docs` 文档
- `area:*`：模块分类，**项目特异**（`whisper-input` 用 `stt/ui/backend/packaging/test/devexp`；其他项目自定义）
- `priority:*`：`P0`（必须做、不做有重大风险）/ `P1`（重大新功能 / 用户能感知的明显问题）/ `P2`（一般小功能 / 偶发问题 / 触发面窄）

`type` 和 `priority` 是项目无关的；`area` 是项目特异的。

### 2. Issue Template 引导规范化

`.github/ISSUE_TEMPLATE/` 至少含三种：

- `feat.md`：动机 / 希望达到 / 候选方向 / 风险 / scope
- `bug.md`：现象 / 根因 / 修复方向 / 风险 / scope
- `spike.md`：问题 / 验证目标 / 方法 / 预期产出 / 关联 issue / scope

每个 template 顶部用 markdown blockquote 占位三轴 label 标注，强制写明优先级判断理由。

### 3. BACKLOG.md 退化为索引

新格式（用 daobidao 现状作蓝本）：

```markdown
# <项目名> — Backlog

未来开发项的**速览索引**。每条都对应一个 GitHub Issue，**详情、讨论、跨轮上下文都在 issue 里**。

## 工作流（此处简介，详细行为由 /backlog / /start / /finish skill 描述）

## P0 — 必须做
- [#N 标题](https://github.com/<owner>/<repo>/issues/N) · `type:feat` `area:stt` —— 一句话理由

## P1 — 重大新功能
- ...

## P2 — 一般小功能小修复
- ...

## 已完成 / 不再追踪
（历史已完成项链接到 closed issues 的查询 URL；下面只列**刻意不做**的项 + 原因）
```

### 4. 工作流改写

| 动作 | 流程 |
|---|---|
| **新增想法** | `gh issue create --template <type>.md` 填模板 → 设三轴 label → 拿到 issue 号 → 在 BACKLOG.md 对应 priority 段加一行 |
| **开新轮** | 从 BACKLOG.md 挑一条 → `gh issue view <N>` 把详情贴进 `docs/N-*/PROMPT.md` 顶部（含 issue 链接）→ 后续讨论也回复到 issue 评论区 |
| **收尾一轮** | commit/PR 描述里写 `Closes #<N>` → push 后 issue 自动关 → 从 BACKLOG.md 删那一行 |
| **SUMMARY「后续 TODO」** | 每条都 `gh issue create` 占位，把 issue 链接补回 SUMMARY 那一段 → 不允许任何想法只活在 SUMMARY 里 |

### 5. 关联到 round 11 的 templates 系统

issue templates（`.github/ISSUE_TEMPLATE/*.md`）是项目级 root-scoped 文件，应当通过 round 11 建立的 `templates/<stack>/__root__/` 机制分发：

- 把 issue templates 加到 `templates/python-uv/__root__/.github/ISSUE_TEMPLATE/`
- bootstrap / sync-project-config 自然会把它们写到新项目里
- 但 `area:` label 是项目特异的，模板里只能放占位符（`<stt|ui|...>`），由项目自己改

至于"area label 列表"是否也由模板管理 → 见后面「待决问题」。

## 范围

### 包含

- **新增/重写四个 skill**：
  - `/backlog`（重写）：改为 `gh issue create --template` 流程，引导填模板 + 设 label，最后追加一行链接到 BACKLOG.md。文件不存在时用新骨架初始化
  - `/start`（小改）：参数若是 issue 号或 issue 链接，先 `gh issue view <N>` 拉详情贴进 PROMPT.md
  - `/finish`（小改）：除了删 BACKLOG.md 行外，确认 commit/PR 描述含 `Closes #N`；并提示「SUMMARY 后续 TODO 是否每条都已开 issue」
  - `/bootstrap`（小改）：选 stack 时一并把 issue templates 复制到项目 `.github/ISSUE_TEMPLATE/`（已通过 round 11 templates 自动覆盖）；新建 BACKLOG.md 时用新骨架（如果项目没有则 bootstrap 自带）
- **添加 issue templates 到 templates/python-uv/__root__/.github/ISSUE_TEMPLATE/**：feat.md / bug.md / spike.md，**area 列表用占位符**
- **改写 GLOBAL_CLAUDE.md** 增加一节"backlog 工作流"，说明三轴 label 约定 + issue 驱动模式
- **本仓库自身 dogfood**：`claude-code-global` 也要按新约定建 issue templates、初始化新格式 BACKLOG.md（当前 BACKLOG.md 是空的，刚好趁机切）；建几个真实 issue 让 BACKLOG 不空

### 不包含

- **历史 BACKLOG.md 数据迁移工具**：当前 `claude-code-global` BACKLOG 已空，不需要迁；其他项目（如 daobidao）已经手动迁完，也不需要工具
- **gh CLI 没安装的兼容**：当前 `claude-code-global` 已 dogfood gh，假设用户机器上有 gh
- **issue 内容跨设备同步机制**：依赖 GitHub 本身，本仓库不做封装
- **多 stack 时 issue templates 的合并**：和 round 11 一样，本轮只做单 stack；多 stack 跨 stack issue templates 合并留至后续 round
- **backlog 排序逻辑自动化**：sort by priority 是人写的，AI 不主动排序
- **跨项目 backlog 聚合视图**：未来想做的话开新 round

## 已拍板的决策（Q1~Q5）

### Q1. area label 列表管理 — A 方案

项目侧维护 `.github/labels.yml`（YAML 列表），bootstrap/sync skill 启动时读它 + 调 `gh label create` 创建对应 label。templates 里提供一个 starter `labels.yml` 含 `type:*` / `priority:*` 全集 + `area:` 占位（一两条样例让用户改）。

理由：A 是 GitHub 生态既有惯例（github/labels 这类工具的事实标准）。B 把 area 写进 marker schema 把"项目语义"和"模板 schema"耦合太紧；C 太松，没人维护就用不了 `gh issue list --label`。

### Q2. bootstrap 时项目无 GitHub remote — 优雅降级

`/bootstrap` 检测 `git remote -v` 没 origin → 写 issue templates 文件**但跳过 `gh label create`**，并在收尾里提示「先 `gh repo create` 关联 GitHub remote，再跑 `/sync-project-config` 走 adopt 把 labels 补上」。

issue templates 文件本身写到 `.github/ISSUE_TEMPLATE/` 不依赖 remote，无害。labels 必须有 remote。

### Q3. `/backlog` 直接调 gh CLI — 直接

AI 与用户对话写出 body 内容（基于 issue template 骨架）+ 选三轴 label → AI 跑 `gh issue create --title ... --body ... --label ...` → 拿到 issue URL → 自动追加一行到 BACKLOG.md 对应 priority 段。

理由：引导让用户拷命令到终端跑，体验断裂、容易拷错；直接调失败时也只是 `gh` 自身报错，可控。

### Q4. SUMMARY.md「后续 TODO」段保留 free-form 写法

**不**强制每条 TODO 必须开 issue。SUMMARY 是回顾文档，TODO 段记录的是「观察 / 可能方向 / 反思」，不一定是"承诺要开发的事"。是否把某条 TODO 升级成真正的开发项是另一次判断，由用户单独决定（届时再 `/backlog`）。

`/finish` **不**主动 `gh issue create`；可以**轻量提示**「如果有 TODO 你想真正推进，单独跑 `/backlog`」，但不强求、不阻塞。

GLOBAL_CLAUDE.md 中「后续 TODO」那段保留原意，不加硬约束。

### Q5. BACKLOG.md「已完成 / 不再追踪」段 — 加进骨架 + `/finish` 软提示

骨架默认含此段（按 daobidao 写法：链接到 closed issues 的 query URL + 一段「刻意不做」的清单）。

`/finish` 在 SUMMARY 写完后，扫「局限性」与「后续 TODO」段，**问用户**有没有"刻意决定不做"的项；有则引导补到 BACKLOG.md「不再追踪」段（每条带原因）。不强制、不自动 —— "刻意不做"是判断不是机械规则。

## 验收

1. **本仓库 dogfood**：本轮结束时，`claude-code-global` 自身有 `.github/ISSUE_TEMPLATE/{feat,bug,spike}.md`、新格式 BACKLOG.md、至少一个真实 issue（可用本轮发现的"后续 TODO"占位）
2. **`/backlog` 端到端**：在测试目录跑 `/backlog`，能引导写 issue → `gh issue create` → 自动加一行到 BACKLOG.md 对应 priority 段
3. **`/start <issue#>` 端到端**：在测试项目用 issue 号开新轮，PROMPT.md 顶部有 issue 链接 + 详情摘要
4. **`/finish` 端到端**：commit message 含 `Closes #N` 后，issue 自动关 + BACKLOG.md 该行被 skill 删掉
5. **templates 同步**：`/sync-project-config` 在已 bootstrap 的项目跑一次，能把新增的 issue templates 同步进去（验 round 11 sync 机制）

## 后续 TODO（不在本轮）

- 跨项目 backlog 聚合视图（一个命令看所有项目所有 P0）
- area label 列表的版本化管理（如果上面 Q1 选 B 方案，深化）
- BACKLOG.md → GitHub Project board 的双向同步
- 历史 SUMMARY.md「后续 TODO」段反向扫描，未关 issue 的批量补 issue
