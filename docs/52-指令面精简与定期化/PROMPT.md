# 指令面按 Claude 5 精神精简，并把「精简」定期化

> 来自 [#84 新增 /routine-slim：每周定时把指令面从「只增不减」拉回平衡（档 A：skills 分层拆分 + 失效引用 + 跨文件去重）](https://github.com/pkulijing/claude-code-global/issues/84)
> Labels: `type:feat` `area:skill` `priority:P1`

## 背景

### 触发点：Anthropic 自己砍掉了 80% 的系统提示

Anthropic 发表 [The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)，公布对 Claude Opus 5 / Fable 5 这类模型**移除了 Claude Code 系统提示的 80% 以上，编码 eval 无可测量的性能损失**。核心判断是「unhobbling Claude」——旧的约束过度限制，且系统内部存在互相冲突的指引；新一代模型能靠上下文与判断力自行推断用户意图。

blog 给出六组 Then → Now：

| # | Then | Now |
| --- | --- | --- |
| 1 | Rules —— 显式细则（"default to writing no comments. Never write multi-paragraph docstrings"） | **Judgment** —— 一般性指引（"Write code that reads like the surrounding code: match its comment density"） |
| 2 | Examples —— 给工具写用法示例 | **Interface Design** —— 用有表达力的参数与结构自然引导行为 |
| 3 | Upfront Context —— 全塞进系统提示 | **Progressive Disclosure** —— 靠 skills / 延迟工具加载按需送达 |
| 4 | Repetition —— 系统提示与工具描述里各写一遍 | **Concision** —— 只写在工具描述里 |
| 5 | Manual Memory —— 人工往 CLAUDE.md 里存 | **Automatic Memory** —— Claude 自动存 |
| 6 | Simple Specs —— 纯 markdown 计划 | **Rich References** —— HTML artifact、代码引用、测试套件、rubric |

对 CLAUDE.md 与 Skills 的直接指引：

> **CLAUDE.md**: "Keep your CLAUDE.md lightweight and briefly describe what your repo is for, but spend most of the tokens on gotchas inside of the codebase."
>
> **Skills**: "Think of skills as lightweight guides to let Claude find information when needed. Avoid making them overconstrained, except in highly important areas."

以及对失败模式的描述：

> "we see several conflicting messages in a single request like 'leave documentation as appropriate,' or 'DO NOT add comments' as our system prompt, skills, and user requests clash with each other."

### 本仓的现状：指令面单向膨胀，且从未净减

issue #84 记录的按月字符数（`GLOBAL_AGENTS.md` + `skills/*/SKILL.md` + `playbooks/*.md`）：

| 月份 | 字符数 |
| --- | --- |
| 2026-04 | 32,495 |
| 2026-05 | 53,355 |
| 2026-06 | 82,611 |
| 2026-07（issue 提出时） | 118,485 |
| **2026-07-31（本轮开轮，master `38d3441`）** | **156,689** |

**四个月 4.8 倍，中间没有任何一次净减。**

开轮实测（本轮基线，含项目 `CLAUDE.md`）：

| 文件 | 字符 | ~token |
| --- | ---: | ---: |
| `playbooks/python.md` | 17,032 | 13,732 |
| `skills/sync-project-config/SKILL.md` | 16,501 | 13,304 |
| `skills/routine-docs/SKILL.md` | 14,311 | 11,538 |
| `playbooks/ros2.md` | 12,012 | 9,685 |
| `skills/bootstrap/SKILL.md` | 11,521 | 9,289 |
| `skills/review-loop/SKILL.md` | 10,731 | 8,652 |
| `skills/finish/SKILL.md` | 10,476 | 8,446 |
| `GLOBAL_AGENTS.md` | 9,922 | 8,000 |
| `playbooks/cloud-routine.md` | 6,354 | 5,123 |
| `skills/devtree/SKILL.md` | 6,280 | 5,063 |
| `playbooks/frontend.md` | 5,586 | 4,503 |
| `CLAUDE.md`（本仓自身） | 5,042 | 4,065 |
| 其余 11 份 | 35,983 | 29,001 |
| **合计** | **161,731** | **~130,401** |

**token 换算率必须实测标定，不能按英文的 4 字符/token 估。** 本轮由 `/context` 标定：`GLOBAL_AGENTS.md` 9,922 字符 = 8k token，即**中文约 1.24 字符/token**。按英文经验值估会把量级低估 3 倍——这个误差本身就是「拍脑袋精简」的典型翻车点。

### 关键判断一：常驻 token 已不是痛点，单次加载密度才是

round51（#70）已把 `rules/` 改名 `playbooks/`，让领域规则文档退出「每会话全文常驻」。**本轮开轮时已实测确认生效**：`/context` 显示 Memory files 仅 11.6k token（`~/.claude/CLAUDE.md` 8k + 项目 `CLAUDE.md` 3.6k），八份 playbook 一份都没被注入。

所以剩下的 ~130k token 全部是**懒加载**的。照搬「省常驻 token」的目标函数会瞄错靶子。真实痛点是两条：

1. **单次加载的指令密度**——`/finish` 一跑就吃 8.4k token 的 SKILL.md，`/sync-project-config` 吃 13.3k；
2. **只增不减的单向棘轮**——没有任何机制把内容拉回去。

### 关键判断二：本仓的膨胀主要来自「重复」和「事故叙事」，不是来自信息量

对照 blog 六个 shift 逐条核到本仓，痛点排序是 **shift 4（Repetition）> shift 1（Rules→Judgment）> shift 3（Progressive Disclosure）**：

- **shift 4 是最大头且零损失**。实例：review-loop 的「三要素并闸 / 高置信过滤 / 2 轮留痕放行」这一套判据，在 **① 宪法「核心开发模式」段、② 宪法「提交前 review」段、③ `review-loop` skill 的 frontmatter description、④ 该 skill 正文「loop 是什么」、⑤ 该 skill Step 6、⑥ `commit` skill 正文** 各写了一遍。同一条规则 6 处表述，删掉 5 处零信息损失。
- **shift 1 有损但有意为之**。本仓大量「禁止 X / 绝不 Y / 有疑则不跳 / 拿不准就偏向 Z」正是 blog 描述的 Then 形态。
- **shift 3 已部分做掉**（round51），剩下的是长 `SKILL.md` → `references/`（本仓已有先例：`skills/finish/references/readme-review.md`；CC 内置 `dataviz` 亦为此形态）。

### 关键判断三：事故记录的问题在形态，不在存在

全仓「事故叙事」措辞（`round N` / 实测 / 真实代价 / 教训 / 硬实证 / 曾…）共 **47 处**，宪法独占 15 处。

人类的原话是「**你总在某次犯过错误之后加一些关于当时怎么犯的错的冗长的描述**」。这个观察准确，但**根因不是「记了 WHY」**——宪法自己写着「注释写 WHY 不写 WHAT」，issue #84 也钉死「事故代价说明一律 keep」，且这些 WHY 每条背后都挂着一次真实返工。**问题在形态**：写成了叙事而非判据。

> 现状：「真实代价：一次猜 host 导致解析层 / 客户端 / 报告层重写、fixture 换掉、测试重做、五处文档返工」
> 应为：「猜 host 曾致全链路返工」

### 本轮最大的风险：LLM 精简器会精准删掉最值钱的部分

**本仓的文档密度是资产不是负债。** LLM 做精简时最容易干的事，恰恰是把「为什么」删掉只留「是什么」——而 WHY 正是本仓区别于通用模板的全部价值。盲目按字数精简会精准删掉最值钱的部分。判据必须钉死**允许删除的封闭清单**与**禁止删除清单**，并继承 `/doctor` check 3 的 "When unsure, keep it"。

## 需求

分两步，顺序不可颠倒。

### 第一步：一次性大精简（真刀真枪改现存内容）

对 `GLOBAL_AGENTS.md` + `skills/*/SKILL.md` + `playbooks/*.md` + 本仓 `CLAUDE.md` 执行**三板斧**（人类已拍板的力度档）：

1. **去重（零损失）**——同一条规则只在**单一真源**写一遍，别处只留指针。预计是最大头。
2. **细则上提为判断原则（有意的信息压缩）**——按 blog shift 1，把成组的「禁止 X / 绝不 Y」合并成一句可判断的原则。
3. **WHY 从叙事压成一句（保留但收缩）**——事故代价、安全禁令、非标约定**一律保留**，但只留结论性的一句，删掉过程叙事。

外加 **progressive disclosure**：超阈值的长 `SKILL.md` 拆出 `references/*.md`，`SKILL.md` 内留明确的「何时去读哪个 reference」指针。

**明确不做**：不做逐条 ablation 删除（即不追问「Claude 5 没有这条会不会做错」进而整条删掉含 WHY）。人类已拍板走保守档，理由是 ablation 判断缺乏实证、误删的规则要靠下次踩坑才发现。

### 第二步：把本次实操中真正可机械化的判据，固化成定期任务

**顺序理由**：issue #84 自己写着「先做量化脚本并跑一遍真实数据 → 看到数再定精简规则 → 写剧本」，本仓也有「避免纸上推演推不出来的洞」的先例（`/routine-docs` 上线前 dry-run 当场改掉两条规则）。所以定期任务的判据必须**从第一步的实操中提炼**，而不是先验地写出来。

产物预期（具体形态待 PLAN 阶段定）：

- **量化脚本**：算常驻 vs 懒加载、每文件 token（**换算率须实测标定**）、与上次基线的 delta。它同时是触发器、dry-run 的基础、以及 PR 里「省了多少」的证据。**没有这个数，精简就是拍脑袋。**
- **精简剧本**（skill）：把三板斧的判据 + 允许 / 禁止删除清单 + 无人值守分岔契约写死。
- **定期触发**：阈值触发而非无条件跑（指令面比上次基线涨超阈值才动手），避免噪音 PR。

## 约束与注意

### 安全边界（硬约束）

- **自我修改边界**：这条定期任务能改 `skills/`，**必须把它自己的 `SKILL.md` 与 `.github/workflows/` 显式排除在可改白名单外**，否则门禁可在改自身时失效。
- **`GLOBAL_AGENTS.md` 的自动改权限需在 PLAN 阶段明确定档**。issue #84 原本把宪法划入「只报告不动手」的档 B；但人类已确认本轮范围含「一次性大精简宪法本身」——需区分「本轮由人 review 的一次性改动」与「定期任务未来能自动改什么」，二者不是一回事。
- 本轮改的是**指令规则文件本身**，按宪法属于「绝不自动跳过 review」的类别。

### 只允许「搬走」不允许「蒸发」

删除型 diff 人 review 起来比新增难得多（**少了什么是看不见的**）。故任何删减都必须能回答三列：**删了什么 / 依据哪条判据 / 这条信息现在从哪读得到**。这一列表是硬要求而非可选。

### 拆 references 的配套义务

拆出 `references/` 后主流程可能漏读关键细节。拆分时必须在 `SKILL.md` 留明确的「何时去读哪个 reference」指针（同宪法对 `playbooks/` 的做法）。

### 验证难题

精简的正确性**无法靠单测覆盖**——「规则删了之后 Agent 还会不会做对」不是一个可断言的命题。PLAN 阶段需给出可操作的验证手段（如：对精简前后的 skill 各跑一次真实流程做对照、或对关键判据保留可检的结构性断言），不能只靠「读起来没丢」。

### 与既有机制的衔接

- CC 内置 `/doctor`（别名 `checkup`）做类似的事，其 check 2/3/4/6 的判据值得直接借用；但它挂不上定期任务（证据源依赖本机 `~/.claude.json` 与 transcript、交互式两道 `AskUserQuestion`、审的对象错位、prompt 打进二进制随版本漂移）。**借判据，不依赖它**。
- 定期任务的出口若沿用 `/routine-docs` 形态（PR 即审批闸，打 `ff-merge` label 或评论 `/ff` 即 FF 合入 master），需复用其已验证的约束。

## 已决（人类在开轮时拍板）

1. **本轮范围**：先精简，再把判据固化成 routine —— 两件事同轮，顺序不可颠倒。
2. **精简力度**：三板斧（去重 + 细则上提 + WHY 压成一句）；**不做**逐条 ablation 删除。
3. **分支基点**：round51 已先行收尾合入 master，本轮基于 master `38d3441` 开。
