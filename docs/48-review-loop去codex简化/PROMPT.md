# 需求：简化 /review-loop —— 放弃 codex 交叉 review，改按 effort 档位分层

## 背景

`/review-loop`（round 45 引入、round 46/47 两轮重构）当前是一个**双档 reviewer** 设计：

- 默认档：CC 自带 `/code-review`；
- 升级档：diff 命中「并发 / 多线程 / 跨进程重试 / 状态机 / 难复现 / 跨 3+ 模块编排」等复杂特征时，升级调 `codex exec review` 做**跨模型独立第二意见**。

升级档还叠了一层「独立性判定」——必须**这段 diff 全部由 CC 编写**且本机 codex 可用，codex 审才算「审的模型 ≠ 写 diff 的模型」，否则回退默认档。

## 问题一：分层把人绕晕了

1. **篇幅与频率倒挂**：`skills/review-loop/SKILL.md` 里 codex 相关内容（Step 2.5 特征判定 + Step 3 独立性判定 + Step 4B 的 PROMPT 四段式组装、stdin 注入安全规则、输出噪音过滤、软防护边界声明）占了全文近一半，而它是**少数派分支**；真正的主路径 Step 4A 只有 7 行。顺序读下来会以为 codex 是主角。
2. **判定链过长**：一次 review 要先过「特征命中？」→「diff 作者是谁？」→「codex 装了吗 / 登录了吗？」三道判定，任何一道不过就回落 CC。三道判定各自都有模糊地带（作者判定尤其——CC 自己也未必知道某段代码是谁写的）。
3. **实际触发率极低**：在本仓库改的基本都是 `skills/*.md` / `GLOBAL_AGENTS.md` / `rules/*.md`——不跳过 review，但也不命中任何复杂特征，codex 档**永远不会自动触发**。为一条几乎跑不到的分支背这么重的文档负担，不划算。
4. **维护面外溢**：codex-as-reviewer 的描述同时铺在 `GLOBAL_AGENTS.md`、`skills/commit/SKILL.md`、`README.md` 三处，任何措辞调整都要四处同步。

## 问题二：review 太费 token

实测：一次 review 直接耗尽一个 session 的 token 预算；**哪怕只改 4-5 行代码也会引发大量文件阅读**。

**根因（读 CLI 2.1.206 二进制中 `/code-review` 实现确认）—— 两条，缺一不足以解释**。

### 根因 A：不传档位就继承 session effort

```js
// 档位解析：l = 显式传入的档位；g_(t) = 当前 session 的 effort
p = c ? (wpe(c, l ?? g_(t)) ?? l) : (l ?? g_(t));
f = p === undefined ? "medium" : yIe(p);
m = Igr[modelFamily][f]; // → cell（prompt 变体）+ modelEffort
```

用户 session 开着 ultracode（xhigh），于是 `/review-loop` 里那句裸调的 `/code-review` 就按 xhigh 跑——审查深度完全不跟 diff 规模挂钩，4-5 行的 diff 与大重构同等规格。

### 根因 B：各档的 review angle 是 **inline** 的，跑在调用方 context 里

`wdb()` 按「模型族 × 档位」选 prompt 变体，各 cell 实际规格：

| 档位     | Opus（`o48-*` cell）                                       | Sonnet / default cell                                           |
| -------- | ---------------------------------------------------------- | --------------------------------------------------------------- |
| `low`    | 1 diff pass，无 verify，≤8 findings                        | 1 diff pass，无 verify，≤4 findings                             |
| `medium` | **8 个 inline angle** → dedup，**无 verify**，≤8 findings  | 3+5 angles × 6 candidates → **1-vote verify**，≤8 findings      |
| `high`   | **8 个 inline angle** → dedup，**无 verify**，≤10 findings | 3+5 angles × 6 candidates → 1-vote verify（recall-biased），≤10 |
| `xhigh`  | 10 个 inline angle → dedup → sweep，≤15 findings           | —                                                               |

三条推论，直接决定本轮设计：

1. **主会话直接跑 `/code-review` = 把 8–10 轮文件阅读永久写进主对话历史**，此后每一轮都要重发。真正掏空 session 预算的是这个复利，不是 review 本身的一次性开销。
2. **Opus 上 `medium` 与 `high` 同为 8 angle、成本几乎相同**（只差 findings 上限 8 vs 10）。「默认 medium、复杂升 high」在纯 Opus 路径上几乎不省钱；唯一的成本悬崖在 `low`（1 pass）↔ `medium`（8 angle）。
3. **自带 verify 的是 Sonnet 档，不是 Opus 档。** Opus 全档位 `no verify`。旧 `SKILL.md` 里「CC `/code-review` 自带 verification step 过滤误报」这句，在默认的 Opus session 下是**假的**。

### 排除掉的**非**成本源（避免后续误判）

- **workflow 多 agent 路由**：`Ldb()` 要求 effort ∈ {high, xhigh, max} **且** feature gate `tengu_review_workflow_routing` 为 true，而该 gate 默认 `false` —— 未触发。
- **finder subagent 扇出**（`clamp(ceil(diffLines/150), 2, 8)` 个 finder）：`Sue()` 工厂默认 `finderBudgetHint: false`，**仅** `claude-sonnet-5` 的 high/xhigh/max 显式开启，Opus 全档位关闭 —— 本次未触发。**但它是个陷阱**：一旦换 Sonnet 又跑 high，反被打开。
- **`/code-review` 内部并无 orchestrator → worker 子 agent 扇出**（曾一度据一段通用 agent 文档误判有）。angle 全是 inline 的，这正是根因 B。

## 需求

**两件事一起做——它们是同一个病根「为小改动付大成本」的两面。**

### 1. 彻底放弃 codex 交叉 review

`/review-loop` 只用 CC 自带的 `/code-review`。删掉升级档、跨模型独立性判定、`codex exec review` 的全部调用细节与配套安全声明、`--codex` / `--cc` 手动覆盖 flag。降级链缩短为「CC `/code-review` → 不可用则本会话自审（显式告知用户）」。

### 2. 分层轴从「reviewer 身份」换成「永远委派 + 两档」

原设计分层在 **reviewer 身份**（CC vs codex）——判定链长、几乎不触发、绕人。新设计只有三条硬规则、一张两行的表。

**硬规则 1：永远显式传档位，绝不裸调 `/code-review`。** 裸调即继承 session effort（根因 A），ultracode session 下即 xhigh，正是本次 token 惨案的直接成因。

**硬规则 2：永远委派给子 agent 跑 review，主会话不直接跑 —— 重档也不例外。** angle 是 inline 的（根因 B），主会话直调会把整轮文件阅读沉进主对话历史并逐轮复利；委派后主会话只收一份 finding 列表。代价是每个子 agent 一份固定的 standing context（系统提示 + `CLAUDE.md` + `rules/*.md` + skills 列表，实测约 5 万 token 量级，绝大部分是可缓存 input）。这笔一次性开销远小于主 context 被撑大后的复利，故委派是**默认**而非某一档的实现细节。

**硬规则 3：合法组合只有两个。** `/code-review` **无模型参数**（flag 白名单仅 `["fix","comment"]`，模型取 `r$(t) = options.mainLoopModel`），唯一可自动化的换模型途径就是委派给指定 `model` 的子 agent（`/model` 是交互式 CLI 命令，skill 无法调起，且会连带换掉写代码的模型）。整个「模型 × 档位」空间里只有两格值得用：

| 档       | 委派                                                       | 命令                  | 触发                                                          |
| -------- | ---------------------------------------------------------- | --------------------- | ------------------------------------------------------------- |
| **默认** | `Agent(subagent_type: "general-purpose", model: "sonnet")` | `/code-review medium` | 一切需要 review 的改动                                        |
| **重**   | `Agent(subagent_type: "general-purpose", model: "opus")`   | `/code-review high`   | 并发 / 多线程 / 跨进程重试 / 状态机 / 难复现 / 跨 3+ 模块编排 |

其余组合明令禁止，各有硬理由：

- `sonnet × high|max` → 打开 finder 扇出（2–8 个 finder 子 agent），比 Opus 还贵；
- `opus × medium` → 与 `opus × high` 同为 8 angle、同价，findings 上限却更低，**被严格支配**；
- 任意 `× xhigh` → 10 angle + sweep，正是本次惨案的规格；且它根本不是 `/code-review` 的合法入参（合法值 `low|medium|high|max|ultra`），只能靠继承 session effort 拿到 —— 硬规则 1 已封死这条路。

**为什么不要第三档（`low`）**：

- `low` 省的是「与 diff 规模成正比」的那部分推理，而小 diff 上这部分本来就小；委派的固定 standing context 才是大头，`low` 省不到它。
- Sonnet 的 `medium` 自带 **1-vote verify**，`low` 没有。review 循环真正的成本大头是**误报引发的无效修复轮**（写测试 → 改代码 → 跑验证 → 复审），不是 review 本身。砍掉 verify 去省 review 的钱，是拿贵的换便宜的。
- 「什么算小 diff」是模糊判断，每次调用都要花推理、还会随时间漂移。删掉这一档等于删掉一次判定。
- 真正琐碎的改动已被「琐碎跳过」判定拦掉了；剩下不跳过的（配置、指令规则文件）恰恰每行都重，不该降规格。

**复杂特征清单原样复用**，只是「升级」的目标从「换个模型审」变成「上强模型 + 加深思考」。

**复审轮不降档**：沿用首轮档位，只在委派 prompt 里把任务收窄为「核对这 N 处 finding 是否已消除、修复是否引入新问题」。收敛由 2 轮硬闸兜底，不必再加一条降档规则。

**委派 prompt 必须携带「已定设计前提」摘要**：子 agent 没有本轮对话上下文，否则会去质疑人类已拍板的决策、制造假 finding。这正是原 Step 0 要解决的问题，现在落在委派边界上。

**委派的已验证事实**（实测子 agent 探测）：① `Agent(model: "sonnet")` 覆盖生效，子 agent 自报 `claude-sonnet-5`；② 子 agent 能看到 `code-review` skill 并跑得起来。

**已知的质量折让**：默认档由 Sonnet 审。可接受，且**并非单纯降级** —— Sonnet 的 `medium` 比 Opus 的 `medium` 多一个 verify 步骤（误报更少），少的是 Opus 的原始推理深度。真正的正确性防线是闸 A（跑代码）：round 47 的教训「基础功能被审废没人发现」是靠跑代码堵的，不是靠 reviewer 更聪明。硬 diff 仍留给 Opus。

## 已决（PLAN 前与人类敲定）

1. **宪法「独立模型 review」小节里那段硬实证**（grpc.aio 重构中 codex 补出 3 个 P1、CC 漏判「优雅停不可达」）→ **降格为「已知局限」保留**。诚实声明：CC `/code-review` 仍是同模型自审，对并发 / 难复现改动存在已知盲区，实证在此；需要跨模型第二意见时由人工手动引入，本 skill 不再自动做。
2. **Step 0「已定设计前提清单」** → **保留语义、并进 6.1 分诊**。删掉独立章节，把「reviewer 质疑一个人类已拍板的决策 → 不算 bug、不阻断、不计入迭代轮数」写成一条分诊规则。收敛判据 (C) 保持不变。

## 明确保留（本轮不动）

`/review-loop` 去掉 codex 后依然有存在价值——下列能力都是 `/code-review` 本身没有的，全部保留：

- **迭代环**：review → 修 → 验证 → 复审，直到收敛（`/code-review` 只出一次 finding）；
- **三要素并闸收敛判据**：(A) 运行验证（受影响测试全绿 + happy-path 主流程跑通，排在 reviewer 意见之前）+ (B) 无高置信 correctness finding + (C) 已定前提未被重复质疑；
- **TDD 正序修复纪律**：先写会红的复现测试、确认旧实现上真红，再改实现；
- **强制人工闸口**：防无限迭代烧 token（**本轮由每 3 轮收紧为每 2 轮**——三轮跑下来人要等太久）；
- **琐碎跳过判定**：纯用户文档 / 注释 / 单行机械 fix 跳过；**配置 + 指令规则文件绝不跳过**；
- **留痕**：每轮结论追加 `docs/<N>-*/REVIEW.md`。

## 明确不动（易误伤，划出边界）

仓库里 `codex` 的提及**分两类**，本轮只碰第二类：

1. **双轨部署语义**——Codex 作为与 CC 并列的 coding agent 端。涉及 `install.sh`、`codex.config.base.toml`、`scheduler/`、`scripts/auto-update.sh`、`rules/*.md` 抬头的双轨说明、`CLAUDE.md`、`skills/commit/SKILL.md` 的 `Co-authored-by` 身份选择、`GLOBAL_AGENTS.md` 的「称呼和语言」「git 规则」两节。**一个字都不改。**
2. **codex-as-reviewer**——本轮要拆除的对象。

## 范围（4 个文件）

| 文件                          | 改动                                                                                                                 |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `skills/review-loop/SKILL.md` | 主体重写：删 Step 2.5 / Step 3 / Step 4B、Step 0 并入分诊；新增「永远委派 + 两档」选档；frontmatter description 重写 |
| `GLOBAL_AGENTS.md`            | 「独立模型 review」小节重写（含改标题）+ 第 36 行、第 51 行两处内联描述同步                                          |
| `skills/commit/SKILL.md`      | 第 4 步（提交前 review loop）精简                                                                                    |
| `README.md`                   | skill 表 `/commit` `/review-loop` 两行 + 第 87 行导语 + 第 198 行工作流串                                            |

## 验收

- `/review-loop` 全文不再出现 codex-as-reviewer 的任何描述，读者从头读到尾只看到一条 reviewer 路径；
- 全文不存在裸调 `/code-review`（无档位）的指示；两档触发条件清晰；
- 全文不存在「主会话直接跑 `/code-review`」的指示（永远委派）；
- 不出现禁止组合（`sonnet × high|max`、`opus × medium`、任意 `× xhigh`）；
- 四个文件描述互相一致、无残留的「升级档 / 独立模型 / 跨模型」措辞；
- 双轨部署语义的 codex 提及完好无损（`grep` 核对）；
- 保留能力清单（迭代环 / 三要素并闸 / TDD 正序 / 2 轮闸口 / 跳过判定 / 留痕）逐条仍在。
