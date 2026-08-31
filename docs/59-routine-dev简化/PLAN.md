# 实现计划：给 `/routine-dev` 减重（刀 A / B / C）

## 关键设计决策（本轮已拍板，review 时不重开）

1. **范围锁死三刀，不做刀 D**（砍自动通道）。本轮**不改变「哪些 issue 会被做」**，只改变「一次运行做多少、怎么收尾、结论存不存」。
2. **安全边界一个字不改**：四条红线、绝不触发合入、绝不发评论、落点白名单、`auto:take` 的授权语义。三刀只删「编排」与「缓存」。
3. **本轮只做整块删除 + 措辞回退**，不做 `/routine-slim` 那种压缩式改写。删掉的东西要么真的不再需要，要么已有别处承载。
4. **历史记录不动**：`docs/DEVTREE.md` 与 `docs/49/52/54/56-*/` 是已发生轮次的记载，其中对 `auto:skip` / 合批 / Step 0.5 的描述**当时为真**，属正常史料，不是失效引用。本轮只在 `/finish` 时追加 round 59 节点。

## 三刀的落点清单

| 文件 | 刀 A（`auto:skip`） | 刀 B（Step 0.5） | 刀 C（一次一条） |
| --- | --- | --- | --- |
| `skills/routine-dev/SKILL.md` | 删 §1.3（5.1 KB）+ Step 1 快照要求 + 1.1 一行 + 1.2 一段 + Step 4「已缓存」段 + Step 5 半段 + 分岔契约一行 + 「明确不做」的写 label 条 | 删 Step 0.5 整节（2.8 KB） | 删 Step 2 整节（2.8 KB）+ `--max-prs`；「落点复核」2.4 KB → ~0.5 KB；全文「批」→「本次」 |
| `.../references/security-boundary.md` | 删 §1 下的「辨析：给 issue 打 `auto:skip`」（1.5 KB） | 删 §3 / §4 / §5（1.6 KB） | 删 §6（1.1 KB） |
| `.github/workflows/auto-skip-reset.yml` | **整文件删**（3.1 KB） | — | — |
| `.github/labels.yml` | 删 `auto:skip` 条目 + 那段注释 | — | — |
| `README.md` | 删「分诊结论会被缓存」整段 + `/routine-dev` `/triage` 行内的 skip 语义 + label 章节一条 | `/routine-dev` 行内措辞 | 同左 + 「撞车防线」段改写 |
| `CLAUDE.md`（项目） | `.github/` 那条里的 `auto:skip` + workflow 描述 | — | routine-dev 描述里的「合批」 |
| `skills/triage/SKILL.md` | 删「自动化」列的 `skip` 语义（只剩 `take`） | — | — |
| `scripts/platform_issue.{py,md}` | **只改注释**：把「为 `auto:skip` 写入方而生」的动机说明改成中性描述 | — | — |
| 远端 GitHub | 删 `auto:skip` label（**一次性人工动作，见「收尾」**） | — | — |

> **`issue-label-add` / `issue-label-remove` / `issue-list --no-body` 三个 helper 能力保留**，不随刀 A 删除 —— 它们是通用能力、有单测覆盖，删了是净损失；只把注释里「为 auto:skip 而生」的动机改中性。

## 刀 C 需要**新增**的两小块（唯一的加法）

删掉合批后，有两件事原先由合批承担，必须补上替代物：

### C-1 · 选哪一条 issue，以及做不成时怎么办（新增）

排序**只用 label 层信息**（不读正文，因此便宜），按序排队：

1. **标记通道优先**（带 `auto:take` 的排前）—— owner 已背书的先做；
2. 同通道内 **`priority` 升序**（P0 → P1 → P2）；
3. 同 priority 取 **issue 号最小**的（最老的优先，防饥饿）。

**分诊短路**：按此序逐条读正文分诊，**第一条合格的即停止分诊、直接进开发**。这顺带把刀 A 删掉的那笔 token 又省了回来 —— 而且是靠「不去读」，不是靠「记住上次读过」。

**开发失败换下一条候选，而不是结束本次运行**（硬规则）。触发它的是开发期的五条分岔：该走 `/start`、撞四条红线、单测收工仍红、`/commit` lint 失败、开 PR 前真实 diff 撞在途 PR。按规范清理步骤（`git reset --hard` + `git clean -fd` + 切回默认分支 + 删分支 + 复检 `git status --porcelain` 为空）收干净后回到排序队列继续往下找 —— **只 `git restore` 清不掉未跟踪文件与已暂存改动**，残留会被 `git checkout` 原样带进下一条候选的分支，**最多尝试开发 3 条**；只有「候选耗尽 / 到 3 次上限 / push 或开 PR 失败（基建故障）」才结束本次运行。

> **为什么必须是硬规则**：排序是**纯函数**、输入每次一样，而刀 A 删掉 `auto:skip` 之后**不存在任何跨运行的记忆**。若「这条失败 = 本次运行结束」，队首那条一旦命中确定性失败（例如它的正文就是要求改红线里的文件），每周三次运行会逐次原地复现同一个失败，后面的 issue **永久轮不到**，而零 PR 又意味着没有任何出口告诉人。这是刀 C（放弃粒度从「这条」升格为「本次运行」）与刀 A（拿掉唯一跨运行标记）叠加出的组合效应，两刀单独看都没问题。

> **残余（如实记）**：3 次上限内若始终是同样那几条排前面且都失败，它们后面的仍轮不到，且那次零 PR 连报告都发不出。缓解只有「只要最终出了 PR，尝试过并放弃的都写进 PR 的「本次未选中」段」。彻底解要么重新引入跨运行持久标记（**与本轮收紧的「绝不打任何 label」冲突，不做**），要么给云端一条真正的输出回路（今天没有）。

> **已知代价（如实记，不粉饰）**：PR 里的「本次未选中」清单只覆盖**检视到中标那条为止**的 issue，不再是全量分诊结论。全量视图由本机 `/triage` 承担，云端不再重复提供。

### C-2 · 落点撞车检查（塌缩，2.4 KB → ~0.5 KB）

原先是「并集 + 逐批比对 + cherry-pick 到已开 PR + 第 1 批特例」四段。现在只剩两条直线检查：

- **开发前**（1.2 排除项表新增一行 + 共享登记文件通则）：该 issue 的**预期落点**与任一 open PR 碰过的文件相交 → 排除，继续找下一条。**「预期落点」必须把共享登记文件算进去**（新增 playbook 要动 `GLOBAL_AGENTS.md` 与 `README.md`，新增 skill 要动 `README.md` 与 `CLAUDE.md`……），否则这道预判形同虚设、会一路做到真实 diff 复核才发现相交。
- **开发后、开 PR 前**：`git diff --name-only origin/<默认分支>...HEAD` 与同一集合比对，相交 → 切回默认分支、`git branch -D` 掉本次分支，**换下一条候选**（同一个 3 次上限），该 issue 下次自然重新捡起（幂等机制保证）。

cherry-pick 到已开 PR 的整条路径**取消** —— 一次只有一个 PR，没有「已开 PR」可并入。

## 三刀的连带收益（写进 SKILL 的「明确不做」，不只是本 PLAN 里说说）

**routine 的写权限面收缩了一圈**，这是三刀的副产品，值得在 SKILL 里明写：

| | 改动前 | 改动后 |
| --- | --- | --- |
| 打 label | 给 issue 打 `auto:skip` | **不打任何 label** |
| push | 新分支 + **force-push 已有 PR 分支** | **只 push 新分支** |
| PR | 开 PR、编辑描述 | 不变 |

原先「绝不给 PR 打任何 label」这条需要配一整节辨析（为什么给 issue 打是安全的）；现在直接收紧成 **「绝不打任何 label」**，辨析随之不必要 —— 这正是刀 A 能连带删掉 security-boundary 那 1.5 KB 的原因。force-push 消失同理带走 §5。

## security-boundary.md 的重编号

删 §3/§4/§5/§6 后剩下三节，**必须重编号为 一 / 二 / 三**（宪法「痕迹形态」表：编号缺口本身就在暗示「这里曾经有过一条」）。连带更新所有跨文件引用：

| 引用处 | 原 | 新 |
| --- | --- | --- |
| `README.md:246` | §7 | §3 |
| `skills/routine-slim/SKILL.md:159` | §2 | §2（不变） |
| `skills/routine-dev/SKILL.md`「明确不做」 | §1 / §2 | §1 / §2（不变） |
| `skills/routine-dev/SKILL.md:205`（§6） | — | 该行随 Step 2 一起删除 |

## 执行顺序

按「先删大块、再补小块、最后收口引用」，每步之后跑一次 `check-refs`：

1. **刀 B**（最独立）：删 SKILL Step 0.5 + security-boundary §3/§4/§5。
2. **刀 A**：删 SKILL §1.3 与全文 `auto:skip` 相关句 + security-boundary 辨析节 + workflow 文件 + labels.yml 条目。
3. **刀 C**：删 SKILL Step 2 + `--max-prs`；写 C-1 选取规则、C-2 撞车检查；全文「批」→「本次」。
4. **security-boundary 重编号** + 更新跨文件 §N 引用。
5. **周边文档收口**：`README.md`、项目 `CLAUDE.md`、`skills/triage/SKILL.md`、`scripts/platform_issue.{py,md}` 注释。
6. **逐条对照安全边界清单**（见验证 4），确认三刀没顺手削弱任何一条。

## 验证（闸 A / 闸 B 各自怎么落）

本轮改的是**指令规则文件 + 一个 workflow + 一条 label 定义**，没有新增可运行逻辑，故 TDD 不适用（宪法「例外」条：无输入输出契约可先写）。验证靠三道机械闸 + 一道人工对照：

| # | 闸 | 命令 / 做法 | 通过判据 |
| --- | --- | --- | --- |
| 1 | 失效引用 | `uv run --no-project scripts/context_budget.py check-refs` | 零失败（**开工前已跑过基线：当前零失败**） |
| 2 | 减重量化 | `uv run --no-project scripts/context_budget.py measure` 前后对比 | `SKILL.md` 落到 24 KB 上下；总指令面下降可量化 |
| 3 | helper 未被改坏 | `uv run --no-project scripts/platform_issue.py --self-test` | 全绿（本轮只改注释，但改了就跑） |
| 4 | 安全边界逐条对照 | 人工：把改动前的四条红线 / 不触发合入 / 不发评论 / 落点白名单原文抄出来，与改动后逐句比对 | 一字未削弱；措辞收紧（如「不打任何 label」）要能说明为什么是收紧不是放松 |
| 5 | `/review-loop` | 每次 commit 前照常跑，**不跳过**（宪法：`skills/*.md` 与配置变更绝不自动跳过） | 三闸并过 |

**闸 A（运行验证）判 N/A 的部分**：SKILL / README / CLAUDE.md 无可运行单元。**不判 N/A 的部分**：删 workflow 与改 labels.yml 属配置变更，由第 3 闸 + 人工核对 YAML 语法承担。

## 收尾：远端 `auto:skip` label 清理（需人类确认）

当前有 **6 条 issue 带 `auto:skip`**（#132 / #124 / #123 / #121 / #115 / #66）。删除 label 会自动把它从这 6 条上摘掉，issue 本身不受影响（它们本就是 open、本就可由人做）。

两点如实说明：

- **`platform_issue.py` 没有 `label-delete` 子命令**，`label-sync-from-file` 只 create / update、**不删除**远端多出来的 label。所以这一步落在 helper 之外。
- 为此专门给 helper 加一个双轨 `label-delete` + 单测，**不值得**（一次性动作、之后无使用者）。故本轮**明确作为一次性人工动作**处理，而不是假装它走了 helper：

  ```bash
  gh label delete 'auto:skip' --repo pkulijing/claude-code-global --yes
  ```

  这条命令**由人类执行或明确授权后再跑**（远端不可逆操作）。不执行的后果：6 条 issue 上留一个不再有任何含义的 label，`/triage` 的「自动化」列会读到它 —— 所以第 5 步会把 `/triage` 改成只认 `auto:take`，即使漏删也不会误导。

## 风险与已知代价

| 风险 | 评估 |
| --- | --- |
| 每周自动产出从「≤5 个 PR」降到「≤3 条 issue」 | **接受**，这正是本轮目的。历史上单次运行也极少出到 5 个 |
| 在途 PR 冲突不再自动修 | **接受**。`ff-merge` 失败会显式暴露，人回本机让 CC 解 —— 本机 uv / gh / agents 全在 |
| 全量分诊结论不再有出口（短路 + 无缓存） | **接受**，全量视图归 `/triage`（本机）。已在 C-1 明写代价 |
| 队首 issue 确定性失败 → 后面的永久饿死 | **由 C-1 的「换下一条候选」兜底**；残余（3 条都失败且零 PR 时不可见）已如实写进 SKILL 与本节 |
| 删多了、把某条安全边界顺手削掉 | **由验证第 4 闸兜底** —— 这是本轮最该防的失败形态，人工逐条对照不可省 |
| 云端 routine 的 prompt 无需改动 | 确认：注册 prompt 只说「调用 `/routine-dev`」，不含任何被删特性的名字 |
