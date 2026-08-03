# SUMMARY · review 成本与思考深度调优

## 开发项背景

`/review-loop` 是提交前的自动门禁，每次 `/commit` 都跑。它委派出去的 reviewer 子 agent **继承主会话的 reasoning effort** —— 主会话在 `xhigh` 时，orchestrator 加 3～5 个 reviewer 全部以 `xhigh` 跑。

表现（issue #98，devops-bot round20 实证，一轮开发跑了 6 次 review）：

- 5 小时额度动辄被 review 吃掉 50%，一次 review 卡住半小时；
- 单轮重档耗时 10–25 分钟、子 agent token 13–23 万；
- 真正阻断的高置信 finding 全轮只有 7 条，且**都来自「多角度独立 + 契约追踪 + 探针验证」**，不是来自某个 reviewer 想得深；
- 同期被置信闸门（`<80 丢弃`）滤掉的低置信项约 20 条，明显是钻牛角尖产物。

**即：花深思考的钱，去生产注定被扔掉的东西。** 而 Agent 工具**没有 effort 入参**，skill 层调不动，只能调模型档。

## 实现方案

### 核心判据（决定了所有档位选择）

调研（Anthropic 官方分模型 effort 建议、AI 代码 review 实践综述、推理深度边际收益实证）与 issue 自身的实证互相印证，收敛成一句：

> **检出率的驱动力是「角度多样性 + 可执行验证」，不是单个 reviewer 的思考深度。深度是这三维里最该砍、砍了最不疼的一维 —— 而且砍它还顺带压低误报。**

支撑本判据的几条关键事实（详细出处见 `PLAN.md` §一、§六）：

- `effort` 影响的是**全部 token 含工具调用次数**（「lower effort → fewer tool calls」）—— reviewer 的成本大头是读文件，降档直接砍读文件次数，不只是「少想一点」；
- `xhigh` 的官方定位是「超过 30 分钟、token 预算以百万计的长任务」，`low` 的典型用例明确写着 "such as subagents"；CC 自己的 `/code-review low` 定位正是「quick check on what you're about to commit」；
- medium→high 存在零边际收益的实证，且**延长推理会让模型放弃原本正确的答案**（overthinking）—— 这解释了那 20 条废品的来源；
- AI 代码**最常错在契约边界**（一个组件的输出成为另一个组件的输入）。

### 动手前先证伪的两条断言

| 断言 | 结论 |
| --- | --- |
| `.claude/agents/*.md` 能钉死 effort | ✅ CC v2.1.220 二进制 zod schema 确认，合法枚举 `EL=["low","medium","high","xhigh","max"]`（官方文档字段说明漏写 `xhigh`，以枚举为准） |
| 软链接的 agent 定义能被加载 | ✅ 实测，**文件级与目录级软链都行**（CC 在 plugin / codex 扫描处有「是软链就跳过」的守卫，这里没有）→ 取目录级，新增 agent 不必重跑 install |
| reviewer 一律降到 `low` | ❌ **被推翻**：官方分模型建议里 Sonnet 5 的 `low` 明确只适用于 "chat and **non-coding** use cases"。Sonnet reviewer 的底是 `medium`（官方称其「相当于 Sonnet 4.6 的 high」） |

### 交付内容

1. **新增 `agents/`（CC 端专有，目录级软链）** —— 编队档位的**单一真源**：
   - `review-orchestrator`（`sonnet` + `medium`，保留 `Agent` 以起编队）
   - `code-reviewer`（`sonnet` + `medium`）
   - `code-reviewer-deep`（`opus` + `medium`，仅重档）

   每个都**显式钉死 `effort` 而非依赖继承**：无论主会话在哪一档，编队成本都确定。工具面同时收紧 —— 去掉 `Edit`/`Write` 把「不改文件」从 prompt 约束变成机制约束；叶子 reviewer 另去掉 `Agent`，堵住再扇出一层的成本失控路径。

2. **`install.sh`** —— `deploy_agent` 加第 5 位置参数 `link_agents`，只在 CC 端链 `agents/`。**没有复用 `config_kind` 当「是不是 CC」的替身**：链不链取决于该端有没有子 agent 这个概念，与配置文件是 JSON 还是 TOML 无关，混用会在将来加第三端时静默链错。

3. **`/review-loop` SKILL.md** —— 成本硬规则从「子 agent 没有 effort 入参」（已被证伪）改为**四维：数量 × 模型 × 思考档 × 范围**，各有各的钉死处；档位表换成专用类型，两档差别改为「角度数 + 深审模型」而非思考深度；补「不要传 `model` 入参」（会盖掉定义里钉死的档）；标明本段是 CC 端路径、Codex 走既有降级链。

4. **角度清单抽到 `skills/review-loop/references/angles.md`** 并写成显式 checklist —— **这是降档的配套条件而非润色**：低思考档会把工作范围收敛到被明确要求的事上，没有清单，降档就等于降检出。同时按调研重排：**① 契约与装配提为首位**，② 缺陷定向扫描（配置/CI 面优先看，再按高频失败形态过），③ 规范合规，重档追加 ④ git 历史、⑤ 并发深审。

5. **安全边界** —— `agents/**` 进两条云端 routine 的禁改清单（`/routine-slim` 永不碰、`/routine-docs` 禁止落点）：改一行 `model`/`effort` 就改了整道门禁的强度，且**改弱了不报错、只会安静地少查出问题**。

6. **上下游同步** —— `GLOBAL_AGENTS.md` 骨架一处措辞、`README.md` 两处编队规格副本收成指针（本仓刚做过同样的「副本已漂移→改指针」重构）、本仓 `CLAUDE.md` 目录结构与注意事项。

### 额外产物

- `docs/53-*/test-agents-link.sh` —— `deploy_agent` 链接行为的 4 组 7 项测试（含「调用点接线正确」一项：函数对了但接错线等于没做）。沿用 `docs/51` 的 `CCG_INSTALL_LIB_ONLY` 先例，在临时 HOME 里只测那一个函数，**不直接跑 `install.sh`**（它的 `REPO_DIR` 取脚本自身目录，在 worktree 里跑会把两端全部软链指向 worktree，worktree 一删全成死链）。
- 一条可复现的自检命令（已写进 `CLAUDE.md`）：`claude -p "…output ONLY the agent type names…" --model haiku` 列出当前生效的 agent 类型。

### 实测结果

| 项 | round 50 旧档（`sonnet` 全 `xhigh`） | round 53 新档（`sonnet` 全 `medium`） |
| --- | --- | --- |
| 编队 | orchestrator + 3 reviewer | 同 |
| **耗时** | **~11 min** | **4 min 25 s** |
| finding ≥80 | 0 | 0 |

transcript 里全程只有 `claude-sonnet-5`、没有 opus → 默认档没误用深审，档位表按预期生效。

## 局限性

1. **⚠ 降档后「难复现 bug 的检出率没掉」没有本地实测背书。** 人类已拍板不做 A/B（A/B 本身要烧的正是本轮想省的额度）。当前依据是三方一致的**推断**：官方分模型 effort 建议 + medium→high 零边际收益与 overthinking 的公开实证 + issue #98 自身在 round20 的实证。
   **本轮那次 review 得到 0 finding 不构成证据** —— round 50 旧档在同类 diff 上同样是 0 条 ≥80。两边都 0 只说明「新档没变得更吵」。
   **失效形态是漏判而非报错，不会自己冒出来。故定下升档判据**：若后续任一轮出现「`/finish` 人工 review 或线上暴露了一个 bug，而该轮 `/review-loop` 判过 clean」→ 把该 diff 存为样本、重跑旧档（`xhigh`）对照，据此决定是否把 `code-reviewer` 升回 `high`。此判据同步写进 issue #98 的收尾评论。
2. **本轮 diff 不含并发 / 状态机代码**，`code-reviewer-deep`（重档专项，`opus`）**这一路从未被真实执行过**，只验证了「默认档不会误用它」。首次跑重档时应留意它是否按预期起得来。
3. **同模型自审的已知盲区依旧**：reviewer 与写 diff 的同为 Claude 模型家族。本轮只动了思考档，没有也不打算改变这一点（跨模型第二意见仍由人工手动引入）。
4. **`agents/*.md` 的 `description` 是常驻指令面**（进每个会话的 Agent 工具类型列表），但 `scripts/context_budget.py measure` 目前不统计 `agents/`，即指令面预算从本轮起有一小块未被计入。

## 后续 TODO

- 把 `agents/*.md` 纳入 `context_budget.py measure` 的统计范围（对应局限性 4）。
- 首次跑重档时确认 `code-reviewer-deep` 起得来、且 `opus` 档位未被 per-invocation `model` 覆盖（对应局限性 2）。
- `install.sh` 被 `source` 时会用调用方的 `$0` 算 `REPO_DIR`，测试脚本必须抢回来。可考虑在 install.sh 里加守卫，避免下一个写测试的人重踩。

## 可沉淀项

本仓即 claude-code-global，按 `/finish` Step 3.3 自指守卫，以下**不跨仓 file**，建议需要时本地 `/backlog`：

| 项 | 判断 |
| --- | --- |
| **新 agent 类型不在当前会话热加载** | 已直接写进本仓 `CLAUDE.md` 开发注意事项 + 自检命令，**无需另起 issue** |
| **`context_budget.py` 未覆盖 `agents/`** | 本仓特有、有明确落点，值得起 issue（见「后续 TODO」第 1 条） |
| **`source install.sh` 覆盖 `REPO_DIR`** | 本仓特有的小陷阱，价值中等，可选 |
| **「降档必须配显式清单」这条通用经验** | 已落在 `angles.md` 顶部与 SKILL.md 里，是本仓资产，无需另立 |
