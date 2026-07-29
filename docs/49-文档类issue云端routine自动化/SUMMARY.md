# SUMMARY：文档类 issue 的云端 routine 自动化 + PR 批准即 FF 合入

## 一、开发项背景

### 希望解决的问题

`the-foundation` round 0 已经把「让 AI 自动化做 routine」的选型讨论透了：**不引入任何框架**，用 Claude Code
自带的 **claude.ai Routines**，靠「`git clone` + `bash install.sh`」在云端复现开发环境；「拉 issue → 分诊 →
改码 → push → 开 PR」整条链路已两轮云端探针实测跑通。但那一轮**只做了选型与能力实测，没写任何一条真 routine**。

本轮把它落成真东西，并解决三个具体诉求：

1. 每天自动扫 open issue，**纯文档类**的走 `/quick` 形态做掉、提 PR 到 `master`；
2. **合理合批**——这类 issue 存量十几条，一条一个 PR 会把 PR 列表淹掉；
3. **PR 批准后要 FF 合入**，不要 merge commit。GitHub 原生的三种合并方式都拿不到真 FF。

### 为什么这三条能一起解

因为 **PR 本身就是审批闸**：routine 出 PR → 手机推送 → 人在手机上决定合不合。这与宪法「人类 review 前移到
`/finish`」是同一个位置，零新增组件。诉求 3 要做的只是把「批准」这个动作的落地方式从 GitHub 的 merge 换成 FF。

## 二、实现方案

### 2.1 关键设计一：FF 合入押在 GitHub 的 "indirect merge" 上

GitHub 官方文档写明——**PR head 分支的提交被直接 push 到仓库默认分支时，该 PR 会被自动标记为 merged**。
于是 `.github/workflows/ff-merge.yml` 做的事就只有一件：在 CI 里 `git push origin <head>:master`。

结果是**「PR 当审批闸」与「master 保持直线历史」两者兼得**：无 merge commit、SHA 不被改写，
与 `/rebase`、`/finish` 的 worktree 收尾是同一套 FF 纪律。

三个设计选择值得记：

- **触发用 label `ff-merge` + 评论 `/ff` 双路，而非 approve review**——自己的 PR 无法自我 approve，
  而 routine 开的 PR 作者就是仓库主人。
- **owner 校验是硬安全边界**：本仓是**公开仓**，任何人都能评论 `/ff`；且它是云端 agent 的信任根，
  谁能推 master 谁就能改云端 agent 的行为。故 `github.event.sender.login == github.repository_owner` 不可省。
- **两个事件都选「workflow 文件恒取自默认分支」的那一档**（`pull_request_target` / `issue_comment`），
  使 PR 内容改不了将要合并它的这段逻辑；job 全程不执行工作区里的任何文件。

失败一律「留评论 + 摘 label」，绝不静默——`ff-merge` label 挂着却什么都没发生，是这条流程最坏的失败方式。

### 2.2 关键设计二：routine 的真逻辑落成 skill，claude.ai 上只留指针

`skills/routine-docs/SKILL.md` 是完整剧本，claude.ai 的 routine prompt 只写一句「clone + install + 跑
`/routine-docs`」。**逻辑全在仓库 → 随 PR 被 review、有版本历史、不会与网页配置漂移**，与「issue 是单一真源」
是同一个偏好。落成 skill（而非新建 `routines/` 目录）还白拿两样：零改 `install.sh`（复用现成的逐目录软链），
以及本机可 `--dry-run` 手动试跑。

剧本里三处是本轮真正想清楚的：

- **两层分诊**：便宜的 label 硬过滤在前，模型读正文判「预期落点是否只在文档」在后。后者不可省——
  `type:feat` 但内容是「沉淀一份 rules 文档」的会被 label 漏掉，`type:docs` 但要改脚本的会被 label 误收。
- **`skills/*.md` 明确排除**：那是门禁自身的逻辑（含这个 skill 本身），不许无人值守自改。
  `GLOBAL_AGENTS.md` / `rules/*.md` 允许改，但 PR 描述要显著标出「本 PR 修改了指令规则文件，请重点 review」。
- **无人值守分岔契约**：本仓多个 skill（`/quick` 的前置判断、`/review-loop` 的 2 轮闸口、`/commit` 的 lint 失败）
  都会「停下来问用户」，而 routine 里没有用户。剧本逐条规定了怎么走（跳过 / 降级并标注 / 放弃该批），
  **绝不允许挂在那里等人**。

### 2.3 开发内容

| 文件                             | 内容                                                                  |
| -------------------------------- | --------------------------------------------------------------------- |
| `.github/workflows/ff-merge.yml` | 双事件触发 + owner 准入闸 + per-PR concurrency                        |
| `.github/scripts/ff-merge.sh`    | FF / rebase-then-FF / 重试 / 轮询确认 merged / 删分支 / 回执评论      |
| `skills/routine-docs/SKILL.md`   | 云端 routine 完整剧本（环境判定 → 分诊 → 合批 → 开发 → 提 PR → 收尾） |
| `.github/labels.yml`             | 新增运维 label `ff-merge`（已 sync 到远端）                           |
| `README.md` / `CLAUDE.md`        | 新 skill 入表、`.github/` 目录说明、FF 合入机制与其硬边界             |

### 2.4 额外产物

- **`.github/scripts/ff-merge.test.sh`**：在沙盘 git 仓上真跑 ff-merge.sh 的**四类路径**（纯 FF / master
  前进需 rebase / 触及 `.github/workflows/` 被判掉 / `/ff` 四种评论形态），gh 用桩替身，**17 条断言**。
  存在的理由很直接：**这段脚本只在 GitHub Actions 里跑，改错了要等真合并才暴露，而那时影响的是 master**。
- **`docs/49-*/DRYRUN.md`**：首次 dry-run 的完整记录（27 条 open issue 的分诊结果、排除理由、合批方案），
  以及它反过来逼出的两条剧本规则。

## 三、过程中真正学到的

### 3.1 dry-run 不是走过场，它改写了剧本

分诊 + 合批规则是纸上写的，跑一遍真实的 27 条 issue 才发现两个洞：

1. **#34 早就被写进 `rules/frontend.md` 了**。剧本原本没有「仓库现状已满足」这条排除项，照原样跑会把
   已经在文件里的内容再写一遍，产出一个纯噪音 PR。→ 「疑似已完成」成为独立排除理由，且要求**动手前去目标文件查一眼**。
2. **落点歧义普遍存在**：#61 #50 #63 都写着「落 `GLOBAL_AGENTS.md` **或**新增 `rules/<topic>.md`」。
   → 默认补进现有文档；新建一份领域规则文档要定触发条件、加宪法指针、影响所有项目的加载面，
   **不该由无人值守的 routine 顺手决定**。

### 3.2 两轮 review 挖出的 6 条，没有一条是我自己会想到的

| 轮次 | 问题                                              | 若不修的后果                                   |
| ---- | ------------------------------------------------- | ---------------------------------------------- |
| 1    | `GITHUB_TOKEN` 无权推 `.github/workflows/` 下文件 | 改 workflow 自身的 PR 走这条路必炸             |
| 1    | `set -e` 下 git 失败绕过 `abort()`                | 无回执、label 不摘——人以为已合、实际什么都没动 |
| 1    | 全局 `concurrency` group 会**取消** pending run   | 一次批 3 个 PR 时中间那个被静默丢弃            |
| 1    | README 说「全程不 checkout」与实现不符            | 会诱导后人往这个 job 里加执行步骤 → 经典漏洞   |
| 2    | `/ff` 匹配没剥 `\r`                               | **网页端多行评论恒不触发**，且不留任何反馈     |
| 2    | 跳过清单承诺了出口，但两条路把载体拿掉了          | 「疑似已完成」这类信号必然丢失                 |

其中第 1 条是**架构级**的：`permissions:` 块里根本没有可声明的 `workflows` scope，提权也绕不过，
只能提前判掉并说明。第 5 条尤其值得记——它恰好落在**测试的盲区**里（原三例全是 `pull_request_target`，
`/ff` 解析路径零覆盖），修完立刻补了 `issue_comment` 的四种正文用例。

### 3.3 「失败方向」比「会不会失败」更值得设计

本轮几处不确定（GITHUB_TOKEN 是否真拒 workflow 文件、GitHub 评论是否真是 CRLF、concurrency 表达式求值）
都无法在本机实测。设计上的应对不是赌它们成立，而是**让每一处的失败方向都是 fail-closed**：
判错了最多是「本该能合的没合、留了条说明评论」，而不是「本不该合的合进了 master」。

## 四、局限性

1. **诉求 3 的核心断言尚未真跑**：「FF push → GitHub 自动标记 merged」目前只有官方文档背书，沙盘只能验
   git 那一侧。同类未实测项：per-PR concurrency 表达式求值、两个事件的字段取值、`GITHUB_TOKEN` 拒推
   workflow 文件、GitHub 评论的 CRLF。**全部 fail-closed**，但「能不能用」要靠第一个真 PR 验。
2. **review 走的是降级链**：`/code-review` 因 `disable-model-invocation` 无法被模型调用（本仓 P0 issue #60），
   主路径与降级链第一档同时不可达。本轮用「委派独立子 agent 做严格手工 review」替代——比本会话自审强，
   但不是 CC 自带的 code-review，**如实标注**。
3. **dry-run 只验了一半**：证明的是「选哪些 issue、怎么分批」合理，**「真写出来的文档质量如何」完全没验过**。
4. **云端整条链本轮没跑过**：install.sh + MCP + push + 开 PR 在 round 0 的探针里跑通过，但跑的不是这个 skill。
5. **测试盲区一处**：`gh pr view` 轮询返回非 MERGED 的分支零覆盖（桩恒返回 MERGED）。
6. **本次零 PR 时跳过清单没有出口**（已在剧本里明写为权衡而非 bug）：PR 是唯一出口，没有 diff 就开不出 PR。
7. **cron 只有小时粒度、走 UTC**：`0 18 * * *` 对应北京 02:00。
8. **`master` 未开分支保护**是有意的（`/finish` 要本地 FF 直推），但这意味着 FF 合入这条 CI 路径的安全
   完全靠 owner 校验兜着。

## 五、后续 TODO

按依赖顺序：

1. **验证链**：本轮合入 master 并 push → 手动跑一次 `/routine-docs --only #72,#73` 出第一个真 PR →
   在该 PR 上打 `ff-merge` 验全链路（PR 是否变 Merged、issue 是否自动关、历史是否仍是直线）→
   再用 `/ff` 评论验第二条触发路径。
2. **验证通过后注册 claude.ai routine**：cron `0 18 * * *`，`sources` 挂本仓。
3. **修 issue #60**（`/code-review` 不可被模型调用）——它让整个 review 闸长期处于降级态。
4. **P0 提醒路径**：round 0 TODO 里「P0 只提醒不动手、在 issue 上留建议评论」，本轮明确不做。
5. 观察几天真实运行后，再判断合批规则的上限（单批 5 条 / 单次 3 个 PR）是否需要调。

## 六、可沉淀项

1. **「给无人值守 agent 写剧本时，必须逐条规定『人不在时怎么走』」**（跨项目通用）：本仓多个 skill 都会
   在为难时停下问用户，这在有人时是优点、在 routine 里是挂死。本轮为此专门列了一张「无人值守分岔契约」表。
   落点建议：`GLOBAL_AGENTS.md` 或未来的 `rules/cloud-routine.md`。
2. **「只在 CI / 远端环境跑的脚本，要配一个本地沙盘测试」**（跨项目通用）：`ff-merge.sh` 改错的代价是
   master，而它永远不会在本地被执行。用「桩 + 临时 git 仓」把主路径跑起来，成本很低、回报很高。
   落点建议：`rules/shell.md` 或 `GLOBAL_AGENTS.md` 测试段。
3. **「dry-run 模式应当是这类自动化 skill 的一等公民」**（跨项目通用）：本轮 dry-run 直接改写了剧本的两条规则。
   若没有它，这两个洞要等第一个垃圾 PR 出来才暴露。落点建议：写进未来的 `rules/cloud-routine.md`。
