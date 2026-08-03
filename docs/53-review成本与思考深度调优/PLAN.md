# PLAN · review 成本与思考深度调优

## 零、先摆实证：两条断言的核实结果

按 `/start` 的「外部行为断言先实证」，动手前先验了 issue 里两条决定设计的技术断言。**一条成立、一条被推翻。**

### 0.1 ✅ `.claude/agents/*.md` 确实能钉死 effort（CC v2.1.220）

直接证据来自二进制里的 agent frontmatter zod schema（`strings` 提取）：

```js
effort: FP().optional().describe("Thinking effort: `low`, `medium`, `high`, `max`, or an integer.")
maxTurns: v.union([v.number(),v.string(),v.null()]).optional()
disallowedTools: Hst().optional().describe("Tools removed from the default set. Ignored if `tools` is set.")
```

合法值枚举在同一二进制里：`EL=["low","medium","high","xhigh","max"]`（describe 那句漏写了 `xhigh`，枚举才是准的）。非法值走 `w("Agent file ... has invalid effort ...")` 告警。

### 0.2 ✅ 软链接的 agent 定义能被加载 —— 且**目录级软链也行**

这条必须实测：本仓所有部署都靠软链，而 CC 在别处（plugin / codex 扫描）有「是软链就跳过，出于安全」的守卫，若 `~/.claude/agents/` 同样守，整个方案就地作废。

复现命令（先建软链，再问一个 headless 会话它看得见哪些 agent 类型）：

```bash
ln -sfn <repo>/agents "$HOME/.claude/agents"
claude -p "Do not use any tools. From the system-reminder listing available agent types for the Agent tool, output ONLY the agent type names, one per line." --model haiku
```

输出含 `ccg-probe`（探针 agent 的 `name`）→ **文件级软链与目录级软链都被正常加载**。取目录级：与 `playbooks/` / `templates/` 同构，**新增 agent 定义不需要重跑 `install.sh`**。

### 0.3 ❌ 被推翻：「reviewer 一律降到 `low`」对 Sonnet 5 是错的

issue 建议 `model: sonnet` + effort 降档，直觉上会一路降到 `low`。但 Anthropic 官方**分模型**的 effort 建议里，Sonnet 5 的 `low` 明确不含编码场景：

> **Low effort:** For high-volume or latency-sensitive workloads. Suitable for chat and **non-coding** use cases where faster turnaround is prioritized.
> **Medium effort:** Cost-saving step-down from the default. Comparable to Claude Sonnet 4.6 at high effort.
> —— [Effort · Recommended effort levels for Claude Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/effort)

→ **Sonnet reviewer 的底是 `medium`，不是 `low`。** `medium` 本身已是「相当于 Sonnet 4.6 的 high 档」，从 `xhigh` 降到它已经是很大一刀；再降一档换来的省，要拿编码判断力去付。

---

## 一、调研结论（PROMPT 要求回答的两个问题）

### Q1 · generally，vibe coding 场景怎么 review？

六条跨来源一致的结论，只取**能改变我们设计**的：

1. **机械门禁是主力，LLM review 是补充。** 「a loop that runs unattended also makes mistakes unattended, and human attention does not scale with agent output」——推荐形态是三段流水线：pre-commit（linter / secret scan / 增量类型检查）→ CI gate（build、diff-scoped SAST、单测+变异+属性测试、e2e、runtime sanitizer）→ post-merge（fuzzing）。结论：**「the throughput gain evaporates if verification stays manual」**。
   → 对我们的意义：`/review-loop` 的**闸 A（运行验证）才是主力**，reviewer 是补充。这条现有设计已经对了，不动。

2. **AI 代码最常错在契约边界。** 「AI-generated code breaks most often where one component's output becomes another's input. When agents refactor services they often change response shapes in ways that don't break unit tests but do break callers.」
   → 我们的角度②「契约与装配」应当**提为首位**并给最细的清单。这也与 issue 的实证吻合：round20 真正阻断的 finding 是**契约追踪**发现的。

3. **失败画像有分布，不是均匀的**：安全漏洞 45%（Java 样本 72%）、**包幻觉 19.6%**（被「slopsquatting」武器化）、可复现性失败 31.7%、重复代码块 2024 年增长 8 倍。
   → 角度清单要**点名这些高频形态**，而不是泛泛说「找 bug」。

4. **「Newer models write cleaner syntax but not safer code」** —— 等下一代模型不是验证策略。
   → 反过来也成立：**用更贵的档跑 reviewer 也不是验证策略**。

5. **范围要小、要计时**：PR diff ≤50 行才能 2 分钟审完，600 行的 diff「rarely is」可审。GitHub 的 timed protocol：1–2 min 扫文件列表与 diff 规模 → 2–3 min **先看 CI / 配置变更**（对抗性动作）→ 3–5 min 扫新增工具函数与重复实现。
   → 「先看配置/CI 变更」这条我们没有，值得吸收进角度清单。

6. **ICSE 2026 对 101 篇文献的系统综述**：QA 是 vibe coding 工作流里最一致被跳过的一环，原因不是不在乎，而是**没有标准 checklist**。高 AI 采用率团队 PR review 中位时长涨 5 倍、每 PR 事故数翻 3 倍。
   → 「给死清单」不是啰嗦，是这件事的核心缺口。

### Q2 · 基于 Opus 5 开发的代码怎么 review？

1. **`effort` 管的是全部 token，不只是 thinking**。官方原话：「lower effort would mean Claude **makes fewer tool calls**」。
   → 这才是省钱的主要机理：reviewer 的成本大头是**读文件**，降档直接砍读文件次数。不是「少想一点」而已。

2. **`low` 档的官方典型用例明确写着 "such as subagents"**；`xhigh` 的定位是「long-running agentic and coding tasks (over 30 minutes) with token budgets in the **millions**」。
   → 我们把一个「审 200 行 diff」的任务跑在为百万 token 长任务设计的档上，档位选错了一个量级。

3. **Opus 5 官方建议**：「Start with `high`, the default … and **use `low` and `medium` liberally as your primary control for token cost and response time** wherever your evals show quality holds.」

4. **低档要配显式清单**：「Opus 4.7 respects effort levels more strictly … At lower effort levels, the model **scopes its work to what was asked** rather than doing more than requested. … **Pair `low` with explicit checklists if your task has multiple sections.**」
   → **降档必须同时把角度写成清单，否则降档等于降检出。** 这是 issue 原方案缺的一块。

5. **CC 自己的 `/code-review` 就是分档的**，官方示例把 **`/code-review low` 定位成「quick check on what you're about to commit」**，`high` / `xhigh` 留给「opening a PR 之前的深度分析」。
   → 我们这个自动环正是「commit 前的 quick check」，Anthropic 自己给它配的就是低档。

6. **深度的边际收益递减有实证**：GPT-5 在 medium 与 high 上同为 97% 准确率、token 却更多（零边际收益）；「increasing the reasoning effort from medium to high does not yield further gains; in fact, performance drops」；code resolution 任务超过 16k thinking token 后递减；且存在 **overthinking** —— 延长推理会让模型**放弃原本正确的答案**。
   → 这解释了 issue 观察到的现象：xhigh 不只是贵，它**主动生产**那 20 条被置信闸扔掉的钻牛角尖 finding。

### 综合判据（本轮所有档位选择的依据）

> **检出率的驱动力是「角度多样性 + 可执行验证」，不是单个 reviewer 的思考深度。**
> 深度是这三维里**最该砍、砍了最不疼**的一维 —— 而且砍它还顺带压低误报。

issue 的实证与调研互相印证：7 条真 finding 全部来自多角度独立 + 契约追踪 + 探针验证；20 条废品全部来自深想。

---

## 二、要做的改动

### 2.1 新增 `agents/` 目录（三个定义，CC 端专有）

| 文件 | `model` | `effort` | 用途 |
| --- | --- | --- | --- |
| `agents/review-orchestrator.md` | `sonnet` | `medium` | 编队、跨 reviewer 去重、置信打分、探针验证 |
| `agents/code-reviewer.md` | `sonnet` | `medium` | 通用角度 reviewer（默认档 3 个 / 重档 4 个） |
| `agents/code-reviewer-deep.md` | `opus` | `medium` | 重档的并发 / 状态机 / 生命周期专项深审 |

**每个定义都显式钉死 `effort`，不靠继承。** 理由：子 agent 默认继承「会话 effort」，而 orchestrator 自己已经被降档 → 链上的继承语义会变得难以推断。逐个钉死后，无论主会话在哪一档，编队成本都是确定的。

**工具面机械收紧**（把「不修改任何文件」从 prompt 约束变成机制约束，同时省掉一批工具定义 token）：

- 叶子 reviewer：`disallowedTools` 去掉 `Edit` / `Write` / `NotebookEdit`，**并去掉 `Agent`** —— 防止 reviewer 自己再扇出一层，那是成本失控的隐藏路径；
- orchestrator：去掉 `Edit` / `Write` / `NotebookEdit`，**保留 `Agent`**（它要起编队）。

**不设 `maxTurns`。**

> ⚠ **`maxTurns` 与 `/review-loop` 的「2 轮不收敛留痕放行」是两个层级的东西，别混。** 后者是**外层**循环（review → 修 → 复审）的终止保护，属宪法骨架第三条，**本轮一个字都不动**（见 §四.9）。这里说的 `maxTurns` 是 agent 定义 frontmatter 的一个可选字段，管的是**单个 reviewer 子 agent 内部的 agentic turn 数**（读一次文件 → 想一步 → 再读一次…）。

不设它的理由：两者的失效形态完全相反。「2 轮留痕放行」是**停环 + 留证据**——遗留 finding 全量写进 `REVIEW.md`，人工判断前移到 `/finish`，没有信息丢失。而 `maxTurns` 是**当场截断**——reviewer 可能刚读完 diff、还没开始审就被掐掉，返回一个空 finding 列表，没审完的部分无声消失。对一道门禁而言，「假 clean」是最坏的失效形态（宁可慢，不可假绿）。

延迟改由 `effort` 控制：低档只会读得少 / 想得少，**不会半路截断**。

### 2.2 `/review-loop` SKILL.md 改写（四处）

1. **成本硬规则第 1 条已被证伪，必须改。** 现文：「子 agent 没有 effort 入参，成本只能靠 reviewer 数量 × 模型 × 任务范围钉死在本 skill 手里」。改为：成本四维 = **数量 × 模型 × 思考档 × 范围**，其中模型与思考档由 agent 定义钉死、不在 prompt 里谈。
2. **「为什么存在」的第三条病根**补一句：成本失控还有一维是**思考档继承**（主会话 xhigh → 全编队 xhigh），并写明这是本轮修掉的。
3. **档位表重写**：

   | 档 | 编队 | 触发 |
   | --- | --- | --- |
   | **默认** | orchestrator ×1 + `code-reviewer` ×3 | 一切需要 review 的改动 |
   | **重** | orchestrator ×1 + `code-reviewer` ×4 + `code-reviewer-deep` ×1 | 命中复杂特征（原表不动） |

   **仍然只有两档、仍然没有更轻档**：真正琐碎的已在 Step 2 跳过；角度数是检出率的主驱动，不能砍。两档的差别现在是**角度数 + 深审模型**，不再是思考深度。
4. **角度分工改写成显式清单**（Anthropic 对低档的官方对策），并按调研重排优先级：
   - **① 契约与装配（提为首位）**：调用点 / 被调方签名与返回形状是否仍匹配、跨文件一致性、diff 是否悄悄改了别人依赖的输出结构、接壤代码是否被破坏；
   - **② 配置与门禁面优先扫**（吸收 GitHub timed protocol 的对抗性动作）：CI / 权限 / 认证 / 部署目标 / 依赖版本的改动排在业务代码之前看；
   - **③ 高频失败形态定向扫**：不存在的包 / API（包幻觉）、错误处理缺失、边界与空值、资源开关未配对、重复实现（已有工具函数没复用）；
   - **④ 项目规范合规**：`CLAUDE.md` / `playbooks/*`；
   - 重档追加 **⑤ git 历史上下文**（blame / 近期相关改动，识别回归）与 **⑥ 并发 / 状态机 / 资源生命周期专项深审**（`code-reviewer-deep`）。
5. **委派段**：`subagent_type` 从 `general-purpose` 改为专用类型；补一句「**CC 端专用**；Codex 端没有 Agent 工具也没有 `agents/` 概念，按既有降级链走」——避免双端共读时 Codex 误判。

### 2.3 `install.sh`：只在 CC 端软链 `agents/`

`deploy_agent` 被两端各调一次。`agents/` 是 CC 独有概念（Codex 没有 `~/.codex/agents/`），故只在 CC 端链接 —— 在 `config_kind = json` 分支内做，或加一个显式开关参数（实现时取更易读的那个）。目录级软链，与 `playbooks/` 同构。

### 2.4 两条云端 routine 的禁改清单加 `agents/`

- `/routine-slim`「永不碰」清单（`skills/routine-slim/SKILL.md`）加 `agents/**`：改 reviewer 的 model / effort **等于改门禁强度**，属安全边界，与 `install.sh` / `scripts/**` / `hooks/**` 同级。
- `/routine-docs` 的禁改面（`skills/routine-docs/references/security-boundary.md`）同样补 `agents/**` —— 它把外部 issue 正文变成文件内容，是 prompt-injection 面，绝不能让它改门禁配置。

### 2.5 上下游文档同步（防漂移）

- `GLOBAL_AGENTS.md` 骨架第 2 条：「成本与 diff 规模挂钩」→ 改为「成本由钉死的模型与思考档控住」（**只改这一处措辞**，三条骨架不变，细节仍以 skill 为单一真源）。
- `README.md` 两处编队规格副本（skill 表格行 + 总览段）：本仓刚做过「副本已漂移 → 改指针」的重构，这里同样**收成一句 + 指向 skill**，不再复述档位细节。
- 本仓 `CLAUDE.md`：目录结构加 `agents/` 一行（含「CC 端专有 / 目录级软链 / 新增无需重装」），开发注意事项相应加一行。

---

## 三、验证计划

本轮交付物是**指令规则文件 + 一处 shell 部署逻辑**，没有「输入 X 应得输出 Y」的代码单元 → 按宪法 TDD 段的例外，不写单测；改为三层可复现的实证。

### V1 · 机制生效（必做，零模型成本）

跑 `bash install.sh`，然后跑 §0.2 那条 headless probe 命令，断言输出包含 `review-orchestrator` / `code-reviewer` / `code-reviewer-deep` 三行。同时检查 `~/.claude/agents` 是软链、`~/.codex/agents` **不存在**。

### V2 · 自举 dogfood（必做，本来就要花的钱）

本轮 diff 含 `skills/*.md` 与 `install.sh`，按 Step 2 **绝不自动跳过**，本来就要走一次 `/review-loop` —— 那次就是新档位的第一次真实运行。在 `REVIEW.md` 里记满一张对照表：**编队规格、耗时、orchestrator token、finding 总数、≥80 条数**，与 round 50 留下的旧档基线（`sonnet` 全 `xhigh`：117,401 token / 24 次工具调用 / ~11 min / 3 reviewer）直接对比。

> ⚠ 已知偏置：本轮 diff 是指令文档，不是并发代码。V2 能证明**成本降了多少**，**不能**证明「难复现 bug 的检出率没掉」。后者要靠 V3。

### V3 · A/B 检出率 —— **人类已拍板：不做**

issue 把它列为待确认项。原样本取不到（`devops-bot` 仓库在本机 `$HOME` 下四层内找不到），本地真实替代样本本可用 round 52 REVIEW.md 记录的 finding #2（`fnmatch` 的 `*` 跨 `/` → `delta` 算出假增长率，置信 90）。**人类决定不做**——A/B 本身要烧的正是本轮想省的额度。

**因此必须诚实承担的后果，写进 `SUMMARY.md` 的「局限性」**：

- 降档的依据是**三方一致的推断**，不是本地实测：① Anthropic 分模型 effort 官方建议；② medium→high 零边际收益 + overthinking 反噬的公开实证；③ issue 自身在 round20 的实证（真 finding 来自契约追踪、废品来自深想）。
- **V2 dogfood 只能证明成本降了多少，证明不了检出率没掉** —— 本轮 diff 是指令文档，不含并发 / 难复现代码。
- **失效形态是漏判而非报错**，不会自己冒出来。故须同时写明**升档判据**：若后续任一轮出现「`/finish` 人工 review 或线上暴露了一个 bug，而该轮 `/review-loop` 判过 clean」，即把该 diff 存为样本、重跑旧档对照，据此决定是否把 `code-reviewer` 升回 `high`。这条也一并落进 issue #98 的收尾评论，避免只留在 SUMMARY 里没人看。

---

## 四、关键设计决策（供 review 时当「已定前提」转传）

1. **降的是思考深度，保的是角度数与运行验证。** 依据：issue 实证（真 finding 来自契约追踪，废品来自深想）+ 调研（深度边际收益递减、overthinking 反噬）。**不砍 reviewer 数量、不砍闸 A。**
2. **Sonnet reviewer 的底档是 `medium` 不是 `low`** —— 官方分模型建议里 Sonnet 5 的 `low` 明确排除编码场景（§0.3）。
3. **每个 agent 定义显式钉死 `effort`**，不依赖继承语义。
4. **不设 `maxTurns`**（单个 reviewer 内部的 turn 上限）—— 截断产出假 clean，是门禁最坏的失效形态。**与外层「2 轮不收敛留痕放行」无关，后者不动。**
5. **`agents/` 只链 CC 端**，目录级软链（已实测可行）。
6. **仍然只有两档，仍然没有更轻档** —— 两档的差别改为「角度数 + 深审模型」，不再是思考深度。
7. **角度清单必须写成显式 checklist** —— 这是降档的配套条件，不是可选的润色（Anthropic 对低档的官方对策）。
8. **`agents/**` 进两条云端 routine 的禁改清单** —— 改 reviewer 档位等于改门禁强度。
9. 三条宪法骨架（运行验证+高置信过滤收敛 / 永远独立 context / 2 轮留痕放行）**本轮不动**。

---

## 五、执行顺序

1. `agents/` 三个定义 → 2. `install.sh` CC 端链接 → 3. **V1 验证**（跑 install + probe，机制不通就地停机）→ 4. `/review-loop` SKILL.md 改写 → 5. 两条 routine 禁改清单 → 6. `GLOBAL_AGENTS.md` / `README.md` / `CLAUDE.md` 同步 → 7. `/commit`（自动触发 **V2 dogfood**）→ 8. `SUMMARY.md`（含 V3 未做的局限性与升档判据）。

（V3 A/B 已拍板不做，不在执行序列里。）

第 3 步是硬关卡：`~/.claude/agents/` 是从零新加的目录，机制不通则后面全是空转。

---

## 六、参考来源

- [Effort — Claude Platform Docs](https://platform.claude.com/docs/en/build-with-claude/effort)（分模型 effort 建议、effort 影响全部 token 含工具调用）
- [Create custom subagents — Claude Code Docs](https://code.claude.com/docs/en/sub-agents)（frontmatter 字段表，含 `effort` / `maxTurns` / `disallowedTools`）
- [Reviewing AI-Generated Code: A Verification Discipline for the Loop — Augment Code](https://www.augmentcode.com/guides/reviewing-ai-generated-code)（三段机械门禁、契约边界、失败画像分布、diff 规模与 timed protocol）
- [Vibe Coding 2026: The Structured Guide to AI-First Development — SitePoint](https://www.sitepoint.com/vibe-coding-2026-the-structured-guide-to-aifirst-development/)（规格前置、角色转为 reviewer）
- [When More Thinking Hurts: Overthinking in LLM Test-Time Compute Scaling](https://arxiv.org/html/2604.10739v1)（延长推理导致放弃正确答案）
- [Do LLMs Overthink Basic Math Reasoning?](https://arxiv.org/pdf/2507.04023)（medium→high 零边际收益）
- [Claude Opus 5: Which Model, Effort, and Limits — agiflow](https://agiflow.io/blog/claude-code-opus-5-subscription-guide)（Opus 5 低档作为成本主控杆）
- [Claude Code PR Review: /ultrareview, Code Review, and Subagents Compared — Shareuhack](https://www.shareuhack.com/en/posts/claude-code-pr-review-subagents-guide) / [Why Claude Code Subagents Burn So Many Tokens](https://youcanbuildthings.com/articles/claude-code-subagents-token-usage/)（子 agent 成本结构、模型路由）
