# PLAN: backlog 工作流改造为 GitHub Issue 驱动

> 详细需求与决策见 [docs/12-backlog改为issue驱动/PROMPT.md](/Users/jing/Developer/claude-code-global/docs/12-backlog改为issue驱动/PROMPT.md)。本文档只列实现路径。

## Context

把 backlog 工作流从「`docs/BACKLOG.md` 是真源」迁到「**GitHub Issues 是真源 + BACKLOG.md 是索引**」。理由：daobidao 项目 30+ 轮实测后，跨轮上下文沉淀在文件里和 git/PR 脱节、删行后历史记忆丢失、裸文本无法 label/query 等问题都浮现，而 issue + `Closes #N` 模型已稳定运行。

涉及四个 skill 改写、三类 issue templates 新增、一份 labels.yml 新增、GLOBAL_CLAUDE.md 一节、本仓库 dogfood。Q1~Q5 五个待决问题已拍板（PROMPT.md 已记录）。

## 实现步骤（顺序）

### Step 1：新增 templates/python-uv/__root__/.github/ 资源

四个新文件，全部 `__root__`-scoped（写到项目根 `.github/`）：

- **`.github/ISSUE_TEMPLATE/feat.md`**：1:1 移植 daobidao 的 feat.md（动机 / 希望达到 / 候选方向 / 风险 / scope；frontmatter 含 `labels: ["type:feat"]`；body 顶部有三轴 label 标注的 blockquote 占位）。area 列表用 `<占位1|占位2|...>` 占位符
- **`.github/ISSUE_TEMPLATE/bug.md`**：同上风格的 bug 模板（现象 / 根因 / 修复方向 / 风险 / scope）
- **`.github/ISSUE_TEMPLATE/spike.md`**：同上风格的 spike 模板（问题 / 验证目标 / 方法 / 预期产出 / 关联 issue / scope）
- **`.github/labels.yml`**：YAML list，含 type/priority 全集 + area 占位（一两条 placeholder 让用户改）。格式：

  ```yaml
  - name: "type:feat"
    color: "0E8A16"
    description: "新功能"
  - name: "priority:P0"
    color: "B60205"
    description: "必须做、不做有重大风险"
  # ...
  - name: "area:placeholder"
    color: "C5DEF5"
    description: "请按项目实际模块自行调整本段 area: 标签"
  ```

文件内容直接基于 daobidao 已实战的版本，AREA 部分占位化。

### Step 2：重写 `skills/backlog/SKILL.md`

完全改语义，新版主流程：

1. **前置检查**：
   - `git remote get-url origin` 必须有 GitHub remote（支持 ssh/https URL）
   - `gh auth status` 必须已登录
   - 当前目录必须有 `.github/ISSUE_TEMPLATE/`（否则提示先 `/sync-project-config` 同步模板）
2. **参数处理**：参数是「这条 backlog 的原始描述」（一句话或半结构化）；无参数则追问
3. **选 type**：用 `AskUserQuestion` 让用户选 feat / bug / spike 之一 → 决定走哪份模板
4. **协作填 body**：基于该模板骨架，AI 按字段引导用户填（缺信息就写「待补充」，不脑补）；对话式来回 1~2 轮即可
5. **选 area**：从项目侧 `.github/labels.yml` 读 `area:*` 列表（如读不到则 fallback 让用户输入），用 `AskUserQuestion` 选一条
6. **选 priority**：用 `AskUserQuestion` 选 P0 / P1 / P2，并要求一句话说明优先级判断
7. **回显草稿 + 三轴 label** 让用户确认（不自动落盘）
8. **执行**：
   - `gh issue create --title "..." --body "..." --label "type:X" --label "area:Y" --label "priority:Z"` → 拿 issue URL
   - 读 `docs/BACKLOG.md`（不存在则用新骨架初始化，见 Step 5）
   - 在对应 priority 段（`## P0 — 必须做` / `## P1` / `## P2`）追加一行：`- [#N <标题>](URL) · \`type:X\` \`area:Y\` —— 一句话理由`
9. **不自动 commit**

### Step 3：更新 `skills/start/SKILL.md`

新增「issue 驱动」分支：

- 参数检测：
  - 如果参数形如 `#数字` 或完整 GitHub issue URL → 走「issue 驱动」分支：
    - `gh issue view <N> --json title,body,url,labels` 拉详情
    - PROMPT.md 顶部写：`> 来自 [#N <标题>](URL)，labels: type:X area:Y priority:Z`
    - body 内容贴到 PROMPT.md 作为「背景 / 需求」段的起点
  - 否则走原有「自由描述」分支（不变）
- 文件夹命名：从 issue 标题或参数中提炼简短中文描述（数字递增 + 描述）

### Step 4：更新 `skills/finish/SKILL.md`

新增/修改的步骤：

1. SUMMARY 撰写后（步骤 1 之后），新增 step 1.5：**扫 SUMMARY 的「局限性」与「后续 TODO」段**，问用户：「有没有刻意决定不做的项要补到 BACKLOG.md「不再追踪」段？」 有则引导用户提供条目 + 原因，写入对应段
2. 步骤 2 改写：「如果 PROMPT.md 顶部含 issue 链接 → 解析出 `#N` → 确保 `/commit` 生成的 message 含 `Closes #N` → 从 BACKLOG.md 删掉对应那行」
3. 步骤 4 走 `/commit` 时，把上一步识别出的 `#N` 作为额外参数（或在 commit message body 里手工加），让 GitHub 自动关 issue
4. 收尾打印一行轻提示：「如果 SUMMARY 的「后续 TODO」里有想真正推进的，单独跑 `/backlog`」

### Step 5：更新 `skills/bootstrap/SKILL.md` —— 模板初始化阶段

当前 bootstrap 已经有 Step 3.{1..4} 模板初始化（来自 round 11）。新增两条副作用动作：

- **Step 3.3 末尾**：如果模板内含 `.github/labels.yml`，且项目有 GitHub remote（`git remote get-url origin` 成功）→ 解析 labels.yml → 对每条调 `gh label create --force "<name>" --color "<color>" --description "<desc>"`（`--force` 在 gh ≥ 2.40 是更新已存在；旧版用 `|| true` 容错）
- **Step 3.4 之后**：如果项目无 `docs/BACKLOG.md` → 写入新格式骨架（见 Step 6 内容），不强制（因为 BACKLOG.md 是 docs/ 下，不属于 templates/scope）
- **若项目无 GitHub remote**：跳过 `gh label create`，收尾里多一行提示「先 `gh repo create`，再 `/sync-project-config`」

### Step 6：BACKLOG.md 新骨架（嵌入 `/backlog` skill 的初始化分支）

`/backlog` skill 在 BACKLOG.md 不存在时落新骨架：

```markdown
# <项目名> — Backlog

未来开发项的**速览索引**。每条都对应一个 GitHub Issue，**详情、讨论、跨轮上下文都在 issue 里**。

**为什么这样组织**：GitHub Issues 是真源（permanent history + 通过 `Closes #N` 跟 commit/PR 永久关联，开发完归档进 closed 仍可检索）。这个文件是当前还没开发的项的扁平快照，方便一眼扫到全图、决定下一轮挑哪个。

## 工作流

- **新增想法** → `/backlog` skill 走 issue templates，挂三轴 label，建完顺手在本文件相应分组里加一行
- **开新轮** → 从下面挑一条 → `/start <issue#>` 把 issue 详情贴进 PROMPT.md → 开干
- **收尾一轮** → PR / commit message 写 `Closes #<issue 号>` 自动关 issue → `/finish` 删本文件这一行

## 三轴分类约定

- **type**：`type:feat` / `type:bug` / `type:refactor` / `type:perf` / `type:test` / `type:docs`
- **area**：模块分类，按本项目 `.github/labels.yml` 中的 area: 列表
- **priority**：`P0`（必须做、不做有重大风险）/ `P1`（重大新功能 / 用户能感知的明显问题）/ `P2`（一般小功能 / 偶发问题 / 触发面窄）

## P0 — 必须做

(暂无)

## P1 — 重大新功能

(暂无)

## P2 — 一般小功能小修复

(暂无)

## 已完成 / 不再追踪

历史已完成项**不在本文件追踪**，直接看 [closed issues with priority labels](https://github.com/<owner>/<repo>/issues?q=is%3Aissue+is%3Aclosed+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2)。

下面只列**刻意决定不做**的条目（避免未来翻老 SUMMARY 误以为是遗漏）：

(暂无)
```

owner/repo 在 skill 落盘时由 `gh repo view --json nameWithOwner` 拿到自动填入。

### Step 7：更新 `GLOBAL_CLAUDE.md`

- 新增一节「Backlog 与开发项管理」放在「项目本地推荐配置」之后，描述：
  - GitHub Issues 是真源
  - 三轴 label（type / area / priority）
  - issue templates 引导
  - `docs/BACKLOG.md` 是索引
  - `/backlog` / `/start <issue#>` / `/finish` 三件套用法
  - `Closes #N` 与 git history 双向链接
- 不动「核心开发模式」中的 SUMMARY「后续 TODO」段语义（按 Q4 决策保持 free-form）

### Step 8：本仓库 dogfood

`claude-code-global` 自身按新规范配置：

1. 把 `templates/python-uv/__root__/.github/ISSUE_TEMPLATE/*.md` 复制到本仓库 `.github/ISSUE_TEMPLATE/`（注意：本仓库不是 python-uv 项目，但 issue templates 是 stack-无关的，复用合理）
2. 创建本仓库 `.github/labels.yml`（type / priority 全集 + area 实际定制：如 `area:install`、`area:skill`、`area:hook`、`area:template` 等本仓库真实模块）
3. 跑 `gh label create ...` 把 labels 推到 GitHub
4. 用新骨架重写 `docs/BACKLOG.md`（当前为空，刚好切）
5. 视情况开 1~2 个 issue 用作 dogfood（如 round 11 SUMMARY 中真正想推进的"后续 TODO"中的某条）—— 由用户在执行时决定具体哪条

### Step 9：实测验证

- bootstrap 端到端（在临时项目里 /bootstrap 选 python-uv，验证 .github/ISSUE_TEMPLATE/ 写入；如有 GitHub remote 验 gh label create 推上去）
- /backlog 端到端（在测试项目里跑 /backlog，验证 issue 被创建 + BACKLOG.md 加行）
- /start <issue#> 端到端（拿一个真 issue 跑 /start，验证 PROMPT.md 顶部有链接）
- /finish 端到端（commit message 含 Closes #N，验证 issue 自动关 + BACKLOG.md 行被删）
- /sync-project-config（在已 bootstrap 的旧项目跑 sync，验证 issue templates 与 labels.yml 被同步）

### Step 10：写 SUMMARY.md，由 `/finish` 收尾

## 涉及文件

### 新增
- `templates/python-uv/__root__/.github/ISSUE_TEMPLATE/feat.md`
- `templates/python-uv/__root__/.github/ISSUE_TEMPLATE/bug.md`
- `templates/python-uv/__root__/.github/ISSUE_TEMPLATE/spike.md`
- `templates/python-uv/__root__/.github/labels.yml`
- `.github/ISSUE_TEMPLATE/feat.md`（本仓库 dogfood）
- `.github/ISSUE_TEMPLATE/bug.md`（本仓库 dogfood）
- `.github/ISSUE_TEMPLATE/spike.md`（本仓库 dogfood）
- `.github/labels.yml`（本仓库 dogfood）
- `docs/12-backlog改为issue驱动/SUMMARY.md`（最后写）

### 修改
- `skills/backlog/SKILL.md`（重写）
- `skills/start/SKILL.md`（加 issue 驱动分支）
- `skills/finish/SKILL.md`（加 issue 关联与「不再追踪」段提示）
- `skills/bootstrap/SKILL.md`（加 gh label create + BACKLOG.md 骨架）
- `GLOBAL_CLAUDE.md`（新增「Backlog 与开发项管理」节）
- `docs/BACKLOG.md`（用新骨架重写；当前为空）
- `docs/DEVTREE.md`（轮次 12 节点；通过 `/devtree` 重建）

## 关键决策与复用要点

1. **不引入 yaml 库依赖**：labels.yml 由 AI 直接读、bootstrap skill 用 jq + python yaml 模块或纯 AI 解析（labels.yml 结构简单，AI 可直接读出后调 `gh label create`）
2. **issue templates 是 stack-无关的**：单 stack 时仍放到 `templates/python-uv/__root__/.github/`，未来如果做 `_common` 伪 stack 再迁移
3. **gh CLI 已在 settings.base.json 的 allow 列表**：复用，不需要新增权限
4. **`/start` 与 issue 双向**：PROMPT.md 顶部记 issue 链接，反向也鼓励用户在 issue 评论里贴 `docs/N-*` 路径作为开发记录链接（这是约定，skill 不强制）
5. **`Closes #N` 与 commit message 集成**：依赖 `/commit` skill 已有的 message 生成能力，不改 commit skill；`/finish` 在调 `/commit` 前把 `#N` 作为额外上下文传入 prompt（让 commit AI 在 message body 自然写上 `Closes #N`）
6. **labels.yml 由 bootstrap 落盘后由 AI 解析 + iterate `gh label create --force`**：不依赖 yq 等额外工具，gh CLI 是唯一外部依赖

## 验证方式

### 1. 模板文件语法
```bash
# yaml 解析
python3 -c "import yaml; yaml.safe_load(open('templates/python-uv/__root__/.github/labels.yml'))"
# issue templates 解析（GitHub 解析 frontmatter + markdown body）
for f in templates/python-uv/__root__/.github/ISSUE_TEMPLATE/*.md; do head -10 "$f"; done
```

### 2. install + 同步
```bash
bash install.sh  # 验证新增的 templates 内容已可被 ~/.claude/templates/ 软链访问到
ls ~/.claude/templates/python-uv/__root__/.github/
```

### 3. /backlog 端到端（人工验证）
- 在本仓库（已 dogfood）跑 `/backlog "测试条目"` → 选 type:bug → 填 body → 选 area + priority → 验证 gh issue 被创建、URL 正常、BACKLOG.md 增加一行
- 创建出来的 issue 在 GitHub 上能看到三个 label

### 4. /start <issue#> 端到端
- 在本仓库跑 `/start <某真 issue 号>` → 验证 docs/13-* 创建、PROMPT.md 顶部有 issue 链接 + 详情贴入

### 5. /finish 端到端
- 在测试项目里跑 /finish → 验证 commit message 含 `Closes #N`、push 后 GitHub 上 issue 自动关、BACKLOG.md 那行被删

### 6. /sync-project-config 端到端
- 在另一个已 bootstrap 但旧的项目跑 /sync-project-config → 验证 issue templates 与 labels.yml 被识别为新增、AI 提案 → accept → 文件落盘

## 风险与边界

- **gh CLI 未登录**：所有依赖 gh 的步骤在 `gh auth status` 失败时优雅降级（写文件、跳过 GitHub 操作、提示用户）
- **gh CLI 版本兼容**：`gh label create --force` 需要 gh ≥ 2.40；旧版用 `|| true` 容错（labels 已存在时跳过）
- **`Closes #N` 写法对非 main/master 分支**：`Closes` 关键字只在 PR 合并到 default branch 时触发自动关 issue。如果用户在 feature branch 直接 commit 不开 PR，需要 push 到 default branch 才生效。skill 不强求，文档提示
- **三个真 issue 同时创建可能 rate limit**：本轮 dogfood 只开 1~2 个 issue，不批量
- **多 stack 时 issue templates 跨 stack merge**：不在本轮范围（与 round 11 一致），单 stack only
