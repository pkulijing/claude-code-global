# 开发总结：/review-loop 去 codex —— 永远委派子 agent + 两档 + 2 轮闸口

## 开发项背景

`/review-loop`（round 45 引入，46 / 47 两轮重构）当时是「双档 reviewer」设计：默认 CC `/code-review`，diff 命中复杂特征才升级引 `codex exec review` 做跨模型独立第二意见。两个问题同时爆发：

**问题一：分层把人绕晕。** 用户直接问「这个 SKILL 把我用晕了，你到底在用 codex 还是 cc 的 `/code-review`」。病因四条：codex 相关内容占 SKILL.md 近一半篇幅却是少数派分支；一次 review 要连过「特征命中？→ diff 作者是谁？→ codex 装了吗」三道判定；在本仓库改的基本都是 `skills/*.md` / `GLOBAL_AGENTS.md`，不命中任何复杂特征，codex 档**永远不会自动触发**；描述铺在四个文件里，改一处要同步四处。

**问题二：review 太费 token。** 实测一次 review 直接耗尽一个 session 的预算，**哪怕只改 4-5 行代码也引发大量文件阅读**。

## 实现方案

### 关键设计

**根因不是猜的，是从 CLI 2.1.206 二进制里读出来的**，而且推翻了两个一开始想当然的判断（详见 `PROMPT.md`「问题二」）：

- **根因 A：不传档位就继承 session effort**（`p = c ? (wpe(c, l ?? g_(t)) ?? l) : (l ?? g_(t))`）。用户 session 开着 ultracode（xhigh），于是 `/review-loop` 里那句裸调的 `/code-review` 就按 xhigh（10 个 angle + sweep）跑——审查深度与 diff 规模完全脱钩。
- **根因 B：review angle 是 inline 的，跑在调用方 context 里。** 主会话直调 `/code-review`，8–10 轮文件阅读会**永久写进主对话历史，此后每轮重发**。真正掏空 session 的是这个复利，不是 review 本身的一次性开销。

两处被证伪的早期判断（都是本轮走过的弯路，记下来防重蹈）：

1. 曾断言「`/code-review` 内部是 orchestrator + `subagent_type: "worker"` 扇出，所以文件阅读不进主 context」——那段字符串其实属于**通用 agent 文档**，不是 code-review 的。真相相反：angle 是 inline 的。
2. 旧 SKILL.md 写着「CC `/code-review` 多 agent 并行 + 独立 verification step 过滤误报」——**在 Opus 上是假的**。各 cell 规格：Opus 全档位 `no verify`；有 1-vote verify 的恰恰是 **Sonnet 档**（`3+5 angles × 6 candidates → 1-vote verify`）。

由此得出的两条反直觉结论，直接定了设计：

- **Opus 上 `medium` 与 `high` 同为 8 个 angle、成本几乎相同**（只差 findings 上限 8 vs 10）。「默认 medium、复杂升 high」在纯 Opus 路径上几乎不省钱。
- **委派 Sonnet 跑 medium 不是单纯降级**——它比 Opus 的 medium 多一个 verify 步骤（误报更少），少的是 Opus 的原始推理深度。

**最终设计：三条成本硬规则 + 两档。**

| 档       | 委派模型 | 命令                  | 触发                                                          |
| -------- | -------- | --------------------- | ------------------------------------------------------------- |
| **默认** | `sonnet` | `/code-review medium` | 一切需要 review 的改动                                        |
| **重**   | `opus`   | `/code-review high`   | 并发 / 多线程 / 跨进程重试 / 状态机 / 难复现 / 跨 3+ 模块编排 |

1. **永远显式传档位**——斩断 effort 继承（根因 A）。
2. **永远委派子 agent 跑 review，重档也不例外**——把 inline angle 的文件阅读关在子 agent 的 context 里（根因 B）。委派不是「Sonnet 路径的实现细节」，它是唯一能保护主 context 的手段。
3. **只用两个「模型 × 档位」组合**。其余明令禁止，各有硬理由：`sonnet × high|max` 会打开 finder 扇出（`clamp(ceil(diffLines/150),2,8)` 个 finder 子 agent）反比 Opus 贵；`opus × medium` 被 `opus × high` 严格支配；任意 `× xhigh` 就是惨案规格、且根本不是合法入参。

**刻意不设第三档 `low`**（用户直接问过「两档够不够」）：`low` 省的是与 diff 规模成正比的那部分推理，小 diff 上本就小，而委派的固定 standing context 才是大头；且 `low` 丢掉 Sonnet 的 1-vote verify，而本 loop 真正的成本大头是**误报引发的无效修复轮**。真正琐碎的改动已被 Step 2「琐碎跳过」拦掉；没跳过的（配置、指令规则文件）每行都重。

**人工闸口由每 3 轮收紧为每 2 轮**（用户要求）：三轮自动迭代跑下来人要等太久；闸口的价值在「早点让人判断值不值得继续」，两轮已足够暴露振荡 / 发散。

**codex 的跨模型价值不假装不存在**：宪法与 SKILL.md 里的 grpc.aio 硬实证（CC 自审只发现 2 个并发隐患，codex 又补出 3 个 P1，「优雅停不可达」CC 完全漏判）**降格为「已知局限」如实保留**，声明需要时由人工手动引入。

### 开发内容概括

四个文件，`skills/review-loop/SKILL.md` 是主体、其余三处是它的摘要：

- **`skills/review-loop/SKILL.md`**：194 → 137 行。删 Step 0（独立章节）、Step 2.5（选 reviewer 档）、Step 3（跨模型独立性判定）、Step 4B（codex 调用的 PROMPT 四段式、stdin 注入安全硬规则、`-c` 保险、输出噪音清单、软防护边界声明）、`--codex` / `--cc` flag。畸形编号（2.5 / 4A / 4B）拉平为连续 6 步。新增 Step 3「三条硬规则 + 两档表 + 禁止组合表」与 Step 4「委派子 agent」。
- **`GLOBAL_AGENTS.md`**：§「独立模型 review」→「提交前 review」，「独立」定义整条删除、换成三条成本硬规则；grpc.aio 实证降格为「已知局限」；闸口 3 轮 → 2 轮；降级链改为「委派 `/code-review` > 主会话 `/code-review` > 本会话自审 > 不 review」。
- **`skills/commit/SKILL.md`** 第 4 步、**`README.md`** 四处：同步为新措辞。

**双轨部署语义**（Codex 作为与 CC 并列的 coding agent 端）划出硬边界、一个字未改：`install.sh`、`codex.config.base.toml`、`scheduler/`、`scripts/auto-update.sh`、`rules/*.md` 抬头、`CLAUDE.md`、`commit/SKILL.md` 的 `Co-authored-by` 身份选择、宪法「称呼和语言」「git 规则」两节。`git status` 核对通过。

### 额外产物

- **`REVIEW.md`**：本轮 review 迭代留痕（7 条 finding → 5 修 2 不阻断 → 复审 clean），含新委派路径的实测 token 数据。
- **四条可机械核验的验收 grep**（`PLAN.md` 第五节）：codex-as-reviewer 清零 / 双轨语义计数无损 / 无裸调 `/code-review` / 无禁止组合。纯文档轮没有单测可写，这四条是它的替代物。
- **CLI 内部实现的一份事实记录**（`PROMPT.md`「问题二」的 cell 规格表）：各模型族 × 各档位的 angle 数、有无 verify、findings 上限、finder 扇出条件。下次要调 review 成本时不必再挖一遍二进制。

### 本轮用新规则审了自己

本 skill 经软链部署，但**软链指向主 checkout 而非 worktree**——这是本轮更正的第三个误判（早期 PLAN 写着「改完即刻生效、本轮会用新规则审自己」）。实际后果：worktree 内改 skill 对当前会话零影响，本轮 `/commit` 读到的仍是旧 skill。既无自举危险，也无自动的活体验证机会。

于是**手动按新 SKILL.md 跑了一遍**，正好当活体验证。新委派路径不仅跑通，还**逮到一个真 bug**：Step 4 的 Agent 委派模板漏了必填字段 `description`，照抄会直接 `InputValidationError`，把本轮的核心机制打废。另修了「硬规则二说永远委派、Step 5 却说降级时主会话直跑」的字面矛盾，和「已定前提清单首轮从哪来」的缺口。1 轮修复即复审 clean，未触及 2 轮闸口。

实测数据佐证了设计：两轮 review 在子 agent 里烧掉 ~32 万 Sonnet token、73 次工具调用，**主会话只收到两份 finding 列表**。

## 局限性

1. **同模型自审的盲区仍在**。`/code-review` 与写 diff 的是同一个模型家族，对并发 / 难复现改动的盲区由 grpc.aio 实证过。升重档（`opus × high`）只是加深思考，不等于引入独立视角。需要跨模型第二意见时得人工手动引入——本轮把这条从「自动机制」降格成了「已知局限 + 人工逃生舱」，是**权衡后的主动取舍**（自动路径的判定链长、触发率近零），不是遗漏。
2. **委派有固定入场费**。每个子 agent 要载入一份 standing context（system prompt + 工具 schema + skills 列表 + `CLAUDE.md` 14,273 字符 + `rules/*.md` 50,340 字符 + 项目 `CLAUDE.md` 5,765 字符 ≈ 7 万字符），实测量级约 5 万 token。绝大部分是可缓存 input，且远小于主 context 被撑大的复利——但在「跑完 review 就结束会话」的一次性场景里，委派是净亏的。
3. **两档的边界靠 Agent 定性判断**。刻意不定硬行数阈值（数字会被机械套用、且本身无依据），代价是「这个 diff 算不算硬」有模糊地带。缓解措施是「拿不准时偏向升重档」。
4. **「禁读敏感文件」指令随 codex 链路一并删除**。这是主动判断：那条指令只约束过 codex 那个**外部进程**，默认的 CC `/code-review` 档从来没有它；委派的子 agent 与主会话处在**同一信任边界**（同为本机 CC、能读的文件完全一样、受同一套权限约束）。已在「明确不做」段写明理由。若未来把 review 交给任何外部模型进程，这条必须加回。
5. **本轮的 cell 规格表会随 CLI 版本漂移**。它读自 2.1.206 的二进制，不是公开契约。若某天 `/code-review` 的行为与文档描述不符，先怀疑这张表过期了。

## 后续 TODO

1. **Codex 端写的代码如何自动引入 CC 做 review**——本轮把 codex-as-reviewer 整条拆了，但反方向的入口（Codex 在写、想让 CC 独立审）从来就没建过。双轨仓库里这是个真实缺口。
2. **验证 `opus × high` 重档的实际成本**。本轮只验了默认档（sonnet × medium）。重档从未真跑过，8 个 Opus inline angle 在子 agent 里到底多贵，没有实测数字。
3. **cell 规格表的过期检测**。目前只能靠人偶然发现。或许可以在 `/review-loop` 里加一条轻量自检（比如观察到 finding 数量或行为明显偏离预期时提示「规格表可能已过期」），但这个想法还很粗。
4. **`README.md` 的 `/review-loop` 表格行已经很长**（一格塞下三条硬规则 + 三要素并闸 + 降级链）。表格作为 skill 索引在膨胀，未来或许该把长描述挪出表格。

## 可沉淀项

本仓库**就是** claude-code-global，故以下按 Step 3.3 自指守卫处理：不跨仓库 file issue，建议用户按需跑本地 `/backlog`。

1. **「Agent 委派模板必须带 `description`」值得进 `GLOBAL_AGENTS.md` 或某条 rules**（去向：宪法 / `rules/`）。本轮亲身踩到：写文档时漏了这个必填字段，照抄即崩。任何 skill 里出现 Agent 委派伪代码都会撞上，跨项目通用。**判定：勉强达标**——落点明确，但目前只出现 1 次，够不上「≥2 次的模式」。倾向先不沉淀，等第二次出现再说。
2. **「注释 / 文档里的事实断言要标注可证伪来源」**（去向：`rules/` 或宪法「文档记录规范」）。本轮三个误判（orchestrator/worker 扇出、Opus 有 verify、软链即刻生效）都是「言之凿凿但没验证」造成的，其中两个已经写进了 SKILL.md 并存活了多轮。**判定：达标**——跨项目通用（任何 Agent 都会在文档里下断言）、落点明确、且本轮一次性撞到三次。**建议跑 `/backlog` 起 issue。**
3. **「改自身的 skill 时，软链指向主 checkout、worktree 内改动不生效」**（去向：`/start` 或 `/review-loop` 的一句提示）。这是 worktree 工作流 + 软链部署并存的必然结果，本仓库每次改 skill 都会撞。**判定：本项目特有**（依赖「软链部署自己的 skill」这个特殊结构），不跨项目。建议本地 `/backlog`。
