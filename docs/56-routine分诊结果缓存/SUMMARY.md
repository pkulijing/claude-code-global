# SUMMARY —— round 56 · routine 分诊结果缓存（`auto:skip`）

> 对应 issue：[#122](https://github.com/pkulijing/claude-code-global/issues/122)

## 开发项背景

`/routine-dev` 每周一 / 三 / 五各跑一次，每次都要把**全部** open issue 重新分诊一遍。Step 1.1 的硬过滤只看 label、成本可忽略；真正花钱的是 **Step 1.2**，它必须读 title + body 才能判定「落点不只在文档上」「需要讨论选型」「正文不足以执行」。

而被判掉的 issue **会长期留在 open 列表里** —— 于是同一批正文每周被完整读三遍、每次得出同一个结论。积压越多，白烧的 token 越多，且只增不减。

## 实现方案

一句话：**把分诊结论回写成 label 持久化，下次在「不读正文」的那一层就滤掉；复活交给 GitHub 的事件系统。**

### 为什么复活机制长这样（这是本轮最主要的设计推导）

要让「补清楚正文之后自动回来」成立，routine 必须能回答「这条 issue 自打标之后有没有被人动过」。这需要一个**打标时刻**的锚点，而三条存法在动手前的实证里全被堵死：

| 候选 | 为什么不通 |
| --- | --- |
| 存进 issue 的机器评论 | 撞 `/routine-dev`「绝不发任何评论」的安全硬规则 —— `ff-merge.yml` 订阅 `issue_comment.created`，routine 从不产生评论才让那条触发路径物理上够不着 |
| 读 timeline 的 `labeled` 事件时间 | 云端无 `gh`、直连 REST 403、内置 MCP 未见该能力，而**云端才是主运行形态** —— 等于优化在生产环境永不生效 |
| 存进仓库文件 | routine 常有零 PR 的运行，那次没有提交落点；且与「issue 是单一真源、无本地索引」相悖 |

于是**干脆不存时刻**：新增 `.github/workflows/auto-skip-reset.yml`，在 issue 被编辑 / 评论 / 重开时直接摘掉 `auto:skip`。routine 侧只需要「加 label」一个写能力。

方案成立的前提也是实证来的：`ff-merge.yml` 订阅的是 `pull_request_target.labeled`，**只对 PR 触发**；给 issue 打 label 发出的是 `issues.labeled`，够不到那条自动合入的路。原文「routine 不打 label」的精确形态其实是「**绝不给 PR 打任何 label**」，本轮一并改准并把推导写进 `references/security-boundary.md` §1。

### 落点

| 层 | 文件 | 内容 |
| --- | --- | --- |
| helper | `scripts/platform_issue.py` `.md` | 新增 `issue-label-add` / `issue-label-remove`（双轨、增量语义、一个 label 一次 flag）；`issue-list` 吐 `updatedAt` 并支持 `--no-body` |
| 平台 | `.github/labels.yml` | 新增 `auto:skip`（描述里写明 ≠ `wontfix`、会被自动摘除） |
| 平台 | `.github/workflows/auto-skip-reset.yml` | **新建**复活闸 |
| 安全 | `skills/routine-dev/references/security-boundary.md` | §1 补「给 issue 打 label 不在触发面上」的辨析 + 新 workflow 的性质 |
| 指令 | `skills/routine-dev/SKILL.md` | Step 1 留时间戳快照；1.1 加过滤行；**新增 Step 1.3**；`--dry-run` / `--only` 语义补齐；分岔契约表加一行；Step 4 要求标 `[已缓存]`；「明确不做」加一条 label 纪律 |
| 指令 | `skills/triage/SKILL.md` | 盘点表加「自动化」一列 |
| 文档 | `README.md` / `CLAUDE.md` | 同步 |

### 深审逼出来的三条硬约束（别当啰嗦删掉）

1. **打标前必须复核时间戳**。复活闸只在 issue **已经带着** `auto:skip` 时才起作用，所以人在本次运行途中做的补救编辑触发不了任何摘标；不复核就会按已作废的旧正文把标打上去，**而编辑的人不知道自己那次编辑没算数**。复核取不到时间戳一律 **fail-closed 放弃打标** —— 代价只是下次再分诊一遍，反过来「取不到就照打」会让这道闸静默失能，恰好埋掉它要防的那件事。`--no-body` 就是为这次复核加的，否则复核要把正文再读一遍，花掉的正是这个 label 要省的钱。
2. **依据「仓库现状」的判定不缓存**（典型：「疑似已完成」）。**缓存的失效信号必须与判定的输入对得上** —— 复活闸感知不到仓库变了，缓存这类判定等于让「这条其实可以关了」这个信号永久消失。同理，**人工轮改动 1.2 判据后要清空全仓 `auto:skip`**：规则本身变了，复活闸同样感知不到。
3. **一条都没打成时要在 PR 里明说**。否则「本次没有可缓存的」和「缓存机制整体失效」在输出里长得一模一样，而云端的时间戳字段尚未实测，后者完全可能。

### 额外产物

- `scripts/platform_issue.py --self-test` 新增：`build_issue_label_cmd` 的 7 组 argv 用例、`_sandbox_issue_label()` 桩测（含**底层非零退出必须透传**）、`updatedAt` 归一与「平台没给就是 `None`」的防兜底用例、`--no-body` 用例。
- `docs/56-routine分诊结果缓存/REVIEW.md`：四次 review 的逐条留痕，含两条被排除的误判与其原因。

## 局限性

- **云端能力仍未实测，这是最大的未知**。云端内置 GitHub MCP 有没有「写 label」和「读到时间戳字段」的工具，只能等下一次真实 routine 运行才知道。已按 fail-closed 设计：取不到就不打标、照常跑，最坏是特性在云端不生效（退回今天的行为），且要求在 PR 里显式报出来、不许静默。
- **复活闸的窗口收窄了但没消灭**。复核与打标之间仍隔着调用间隙，人恰好在那几秒动手仍会被吞掉。已规定复核紧邻打标循环之前做、一口气打完（循环不读正文、通常秒级），并写明不要靠「打完再读一次」闭环（`issue-label-add` 自己会 bump 时间戳，必然 100% 误报）。
- **GitLab 侧未经实测**：本机没装 `glab`，`issue-label-add` / `-remove` 的 GitLab 分支只由纯函数 + 桩测钉住 argv 形态，真实 flag 语义待有 GitLab 环境时校（与 `issue-comment` 的 GitLab 输出 schema 同属一类未验项）。
- **`skills/routine-dev/SKILL.md` 那个 commit 跑满了 `/review-loop` 的 2 轮上限**：两轮共 9 条 finding 全部已修，但第 3 轮确认复审没跑（上限即停）。逐条见 `REVIEW.md`。
- **label 不带理由**：被缓存的那批在 issue 上看得见「被判掉了」，但**为什么**被判掉仍只活在那次运行的 PR 描述里；零 PR 那次连这个都没有。

## 后续 TODO

- **合入后手工验一次复活链路**（必做）：`on: issues` 类 workflow 只有默认分支上的版本才会被触发，所以本地验不了。步骤：给一条测试 issue 打上 `auto:skip` → 编辑其正文 → 看 Actions 里有没有一次 run、label 有没有被摘掉。
- **下一次云端 routine 跑完后核对**：PR 里有没有 `[已缓存]` 行；若报了「一条都没打成」，去确认是缺 label 写工具还是缺时间戳字段，并把结论回写进 `playbooks/cloud-routine.md` 的能力矩阵。
- **观察实际省了多少**：几轮之后看看被缓存的比例，判断这个机制值不值它带来的复杂度。
- 「routine 绝不发评论」这条规则用户认为过于保守、想讨论掉。**本轮一个字没动** —— 它正是把「留机器评论存时间戳」那条路挡掉的规则。要改的话建议单开一轮，把 `references/security-boundary.md` §1 的攻击链重新推一遍再决定。

## 可沉淀项

本仓即 claude-code-global，按 `/finish` Step 3.3 自指守卫，下列不跨仓 file，建议本地 `/backlog` 起 issue：

1. **reviewer 在 worktree 轮里读错了 checkout**（本轮真实发生）→ **已起 [#123](https://github.com/pkulijing/claude-code-global/issues/123)（P1）**。一个 reviewer 报「helper 缺 `--no-body` / `issue-label-add`」，实为它读的是主仓库 checkout（仍在 `master`）而非本 worktree 的同名文件。**机制**：子 agent 继承的是会话的主工作目录，继承不到主会话 shell 的 `cd`；委派 prompt 写了绝对路径也只是「告知」，没有任何机制要求它在那儿操作。**真正的风险在反方向** —— 主 checkout 里常有别的未提交改动，reviewer 会认真审完一堆无关内容然后报 clean，而失败完全静默。落点见 issue。
2. **「缓存 / 记忆型机制的失效信号必须与判定的输入同源」**：本轮两次踩到同一形状 —— 缓存了「依据仓库现状」的判定、以及规则本身变了缓存却不失效。这是个可写成一句话的通用判据，落点是宪法或某份 playbook。
3. **新增会产生外部副作用的步骤时，要回头同步 `--dry-run` 与同类开关的语义**：本轮 `--dry-run` 需补「不打任何 label」、`--only` 需补「含 1.3」，都是深审才捞出来的。落点：宪法「无人值守 / dry-run 是一等公民」那段，或 `playbooks/cloud-routine.md` §5。
