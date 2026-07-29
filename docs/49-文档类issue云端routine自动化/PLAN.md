# PLAN · round 49：文档类 issue 的云端 routine 自动化 + PR 批准即 FF 合入

## Context

`the-foundation` round 0 已经把「让 AI 自动化做 routine」的选型讨论透了，结论是**不引入任何框架**，
用 Claude Code 自带的 **claude.ai Routines**，靠「`git clone` + `bash install.sh`」在云端复现开发环境；
「拉 issue → 分诊 → 改码 → push → 开 PR」整条链路已两轮云端探针**实测跑通**。但那一轮**没写任何一条真 routine**，
它的 TODO 第 1/2/3 条正是本轮的正题。

本轮把这条已验证可行的链路落成真东西，并解决三个具体诉求：① 每天自动扫 open issue、纯文档类的走 `/quick`
形态做掉并提 PR；② 合理合批，不要一个 issue 一个 PR；③ **照常提 PR 保住手机上 review 的审批闸，但「批准」
触发的是一次真 fast-forward，不是 GitHub 的 merge**——本仓一贯要直线历史（`/rebase`、`/finish` 都按 FF 做）。

**诉求 3 的可行性已用文档实证**：GitHub 官方文档的 "indirect merge" 条款写明——当 PR head 分支的提交被
**直接 push 到仓库默认分支**时，该 PR 会被**自动标记为 merged**。本仓 `master` 是默认分支、当前**未开分支保护**、
Actions 已启用（默认 token 权限 read，workflow 内显式声明 `contents: write` 即可提权）。故「CI 里 `git push
origin <head>:master`」＝ 一次真 FF，且 PR 自动变 Merged、commit 里的 `Closes #N` 自动关 issue。

## 已定的四个决策（本轮按此执行）

| 决策点           | 定论                                                                     |
| ---------------- | ------------------------------------------------------------------------ |
| 批准触发方式     | **label `ff-merge` 与评论 `/ff` 都支持**，同一段逻辑 + 发起人 owner 校验 |
| routine 剧本落点 | **skill `/routine-docs`**（零改 `install.sh`，本机可 `--dry-run` 试跑）  |
| 本轮范围         | **只做文档类自动开发**，P0 提醒路径另开 issue                            |
| cron             | **北京时间每天 02:00 = UTC 18:00**（`0 18 * * *`）                       |

---

## 交付物 1：`.github/workflows/ff-merge.yml`（新增）

批准即 FF 合入。**这是本仓第一个能自动写 master 的机制，而本仓是云端 agent 的信任根，安全校验是设计的一部分。**

```yaml
on:
  pull_request:
    types: [labeled] # 打 ff-merge label
  issue_comment:
    types: [created] # 评论 /ff
permissions:
  contents: write # 仓库默认 token 是 read，必须在此提权才能 push master
  pull-requests: write # 回评论 / 摘 label
concurrency: { group: ff-merge, cancel-in-progress: false } # 两个 PR 同时批准要串行
```

作业逻辑（单 job，用 `gh` + `git`，`actions/checkout` 带 `fetch-depth: 0`）：

1. **准入三闸**（任一不过就静默退出）：
   - 事件匹配：`labeled` 且 label 名 == `ff-merge`；或 `issue_comment` 且是 PR 上的评论、正文首行 == `/ff`。
   - **发起人 == 仓库 owner**（`github.event.sender.login == github.repository_owner`）。**本仓是公开仓，
     任何人都能评论 `/ff`**，这一闸是硬安全边界；label 那条路虽然天然只有写权限的人能打，同样过这一闸。
   - PR 状态为 open、非 draft、非来自 fork（fork PR 的 `pull_request` token 恒为只读，会失败，提前判掉并说明）。
2. **取 PR head SHA 与 head 分支名**（`gh pr view --json headRefName,headRefOid,baseRefName`），校验 base == `master`。
3. **FF 尝试**：`git merge-base --is-ancestor origin/master <head>`
   - **成立** → `git push origin <head>:master`（纯 FF，不带 `--force`）。
   - **不成立**（master 在 review 期间前进了）→ `git rebase origin/master` 后 force-push 回 PR 分支，再 FF push。
     **冲突则 `rebase --abort`、评论说明、摘掉 label、退出**，绝不硬合。
     这与 `/finish` §8.3 的 worktree 收尾语义完全一致（rebase → `--ff-only`，冲突 abort 兜底），
     只是把同一语义搬到远端。**残余风险**：文本无冲突但语义变（纯文档批次概率极低），故第 5 步把新旧 SHA 都评出来。
4. **善后**：删 head 分支；GitHub 自动把 PR 标记为 merged、`Closes #N` 自动关 issue（无需 CI 干预）。
5. **回执评论**：`已 FF 合入 master：<旧 master SHA> → <新 SHA>`（若发生 rebase，附「原 SHA → 重放后 SHA」）；
   失败时评论失败原因并摘掉 `ff-merge` label，便于重打重试。

## 交付物 2：`skills/routine-docs/SKILL.md`（新增，本轮主体）

云端 routine 的**真逻辑**。claude.ai 上的 routine prompt 只写一句「clone + install + 跑 `/routine-docs`」，
逻辑全在仓库里随 PR 被 review——与「issue 是单一真源」同一个偏好，避免配置漂移。

**args**：`--dry-run`（只输出分诊 + 分批结果，不改码不提 PR）、`--only #N[,#M]`（只处理指定 issue，供手动验证）。

### Step 0 · 环境判定与前置闸

- **云端 vs 本机**：`command -v gh` 探测。云端 `gh` 未装、raw GitHub API 403 → issue 读写与开 PR **一律走内置
  GitHub MCP**；本机 → issue 走 `scripts/platform_issue.py`、开 PR 走 `gh pr create`。
  （round 0 实测：`platform_issue.py` 云端不可用，因为它包的就是 `gh`/`glab`。）
- 前置闸：工作树干净、当前在 `master` 且已 `git pull` 到最新；否则中止。

### Step 1 · 拉 open issue 并两层分诊

- **硬过滤**（先便宜地砍掉大头）：排除 `priority:P0`、排除 `wontfix`、排除 `area:install` / `area:hook`、
  排除已被现有 open PR 覆盖的（见 Step 4 的幂等机制）。
- **模型分诊**（round 0 认定 Routines 原生具备的能力）：读 title + body，判定是否**纯文档类**——
  判据是「预期改动只落在 `rules/*.md` / `GLOBAL_AGENTS.md` / `README.md` / `docs/`，**不改任何可执行面**
  （`install.sh` / `hooks/` / `scripts/` / `templates/` / `skills/`）」。
  **`skills/*.md` 明确排除**：它是指令规则文件、改的是门禁自身，不能无人值守自动改。
  这一层保证像「`type:feat` 但内容其实是沉淀一份 rules 文档」这类 issue 不被 label 硬过滤漏掉。
- **需要讨论 / 选型 / 有分歧 / 要落 PLAN 追踪的一律排除**（那些该走 `/start`，不是 `/quick`）。

### Step 2 · 合批规则（诉求 2）

不是硬编码数量，是一组可判断的规则：

1. **同落点文件优先合批**（都写 `rules/python.md` 的合成一批）；
2. 落点不同但**主题同源**的小簇可并批（如都属飞书栈、都属流程纪律）；
3. 单批 ≤ 5 个 issue，单批预期 diff 过大则拆；
4. **单个 issue 预期新建整份文档**（如一份全新的 `rules/*.md`）→ **独占一个 PR**；
5. 单次运行 ≤ 3 个 PR，超出的自然留到明天——存量十几条会在几天内自然消化完。

### Step 3 · 逐条开发（复用 `/quick`，不重写一套）

每批开分支 `auto/docs-<YYYYMMDD>-<主题>`（从最新 master 切），批内逐条 issue 调 **`/quick #N <描述>`**——
分诊已由本 skill 承担，`/quick` 的前置判断在此不再重复。**per-issue 一个 commit**（各带 `Closes #N`，
多个 issue 时每个 `Closes` 独占一行），保住「一条 issue = 一个可单独回退的提交」。

**无人值守分岔契约**（本仓多个 skill 都会「停下问用户」，routine 里没有用户，必须逐条定死）：

| 分岔                                         | 有人在环时   | routine 里                                                        |
| -------------------------------------------- | ------------ | ----------------------------------------------------------------- |
| 开发中发现该 issue 其实该走 `/start`         | 反问用户     | `git restore` 该条改动、跳过，记入 PR 的「本次跳过」段            |
| `/review-loop` 自动修复满 2 轮未收敛         | 停下交回用户 | 停止修复、保留现状，未收敛项写进 PR 描述——**PR 就是那个人工闸口** |
| `/review-loop` 降级（`/code-review` 不可用） | 告知用户     | 照常继续，**在 PR 描述如实标注「未经独立 review 把关」**          |
| `/commit` lint 失败                          | 停下问用户   | 放弃该条、`git restore`、记入跳过清单                             |
| push / 开 PR 失败                            | 问用户       | 放弃该批，不重试                                                  |

> 已知：issue #60（`/code-review` 因 `disable-model-invocation` 无法被模型调用）会让 review 闸大概率走降级链。
> 本轮**不修**它，只保证降级路径明确且在 PR 里如实标注。

### Step 4 · 提 PR + 幂等

PR body 模板固定含：合批的 issue 清单（每条 `Closes #N` 独占一行）、每条的改动摘要、review 档位与是否降级、
本次跳过清单、以及一行「**打 `ff-merge` label 或评论 `/ff` 即 FF 合入 master**」。

**幂等机制**：每次运行先列 open PR、解析 body 里的 `Closes #N` 得到「已在途 issue 集合」，Step 1 硬过滤时排除。
**PR 列不出来就中止本次运行**（宁可不跑，不可重复做同一条 issue）。

### Step 5 · 汇报

有 PR → PR 即汇报出口（round 0：云端**无编程可读回路**，任何 routine 都必须自带出口）。
**无候选 → 静默结束**，不制造噪音、不留空提交。

### Step 6 · skill 内附「如何注册到 claude.ai」

把要粘到 routine 里的那句 prompt 与 cron 表达式写进 skill 末节，让机制自解释。

## 交付物 3：配套改动

- **`.github/labels.yml`**：新增「运维（三轴之外）」段，加 `ff-merge`（描述写明「打上即触发 FF 合入 CI」）；
  执行阶段跑 `platform_issue.py label-sync-from-file` 推到 GitHub，否则打不了这个 label。
  （本仓的 labels.yml 已是项目定制版、与 `templates/_common` 的模板早已分叉，加这段不冲突。）
- **`README.md` / `CLAUDE.md`**：目录结构补 `.github/workflows/`；说明新 skill、FF 合并约定、
  以及「新增 skill 后需重跑 `install.sh`」这条既有注意事项在本轮的适用。

## 交付物 4：注册 claude.ai routine

`/schedule` 建一条 cron `0 18 * * *`（UTC）的 routine，`sources` 挂本仓，prompt 只写
「clone + `bash install.sh` + 跑 `/routine-docs`，一切以 `skills/routine-docs/SKILL.md` 为准」。
**这一步在验证链跑通之后、且经你点头再执行**（它是对你 claude.ai 账号的外部写操作）。

---

## 验证方案（诉求 3 的实证不能只靠文档）

1. **YAML 门禁**：`actionlint` 或至少 `yaml.safe_load` 验 `ff-merge.yml` 合法。
2. **本机 dry-run**：`/routine-docs --dry-run` 跑真实的 27 条 open issue，人工看分诊与分批结果是否合理。
3. **本轮自身收尾**：`/finish` 本地 rebase + FF 合 master 并 push——workflow 与 skill 由此上线
   （workflow 必须先在默认分支上，`issue_comment` 触发才认）。
4. **手动跑一次真链路**：`/routine-docs --only #72,#73` → 产出第一个真 PR（会推分支、开 PR，**推之前找你确认**）。
   这既是 dogfood，也顺手把 round 0 遗留的两条沉淀 issue 做掉。
5. **FF 机制实证**（本轮最关键的一步）：在该 PR 上打 `ff-merge` label → 观察：
   Action 是否成功 FF push、**PR 是否自动变 Merged**、`Closes #N` 是否自动关 issue、head 分支是否被删、
   `git log --graph` 是否**无 merge commit、保持直线**。再用 `/ff` 评论在下一个 PR 上验证第二条触发路径。
6. **验证通过后**才注册 cron routine（交付物 4）。

## 风险与明确不做

- **信任根风险**：本轮给了 CI 一条自动写 master 的路。缓解＝ owner 校验 + 只 FF 不强推 + 冲突即停 + 回执评论。
  仍建议后续考虑 master 分支保护（round 0 TODO 第 4 条，**本轮不做**，因为开保护会挡住 `/finish` 的本地 FF 直推）。
- **本轮不做**：P0 提醒路径、修 issue #60、`rules/cloud-routine.md`（#72）与宪法云端分野标注（#73）的**内容本身**
  ——后两者留给第 4 步由 routine 自己做掉，正好当作端到端验证。
- **cron 只有小时粒度、走 UTC**：`0 18 * * *` 对应北京 02:00，夏令时无关（中国不实行）。
