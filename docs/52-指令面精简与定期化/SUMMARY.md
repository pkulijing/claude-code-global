# Round 52 总结：指令面按 Claude 5 精神精简，并把「精简」定期化

> Closes #84

## 开发项背景

### 希望解决的问题

Anthropic 发布 [The new rules of context engineering for Claude 5](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)，公布对 Opus 5 / Fable 5 **移除了 Claude Code 系统提示的 80% 以上，编码 eval 无可测量的性能损失**。核心判断是旧约束过度限制、系统内部存在互相冲突的指引，而新一代模型能靠上下文与判断力自行推断意图。

本仓的指令面正是那个形态，且**单向增长、从未净减**：

| 月份 | 字符数 |
| --- | --- |
| 2026-04 | 32,495 |
| 2026-05 | 53,355 |
| 2026-06 | 82,611 |
| 2026-07（issue #84 提出时） | 118,485 |
| 2026-07-31（本轮开轮） | **162,562** |

人类提 issue 的原话是：「**你总在某次犯过错误之后加一些关于当时怎么犯的错的冗长的描述。**」

这个观察准确，但**根因不是「记了 WHY」**——宪法自己写着「注释写 WHY 不写 WHAT」，每条 WHY 背后都挂着一次真实返工。问题在**形态**：写成了叙事而非判据，且同一条规则在多处各写一遍。

## 实现方案

### 关键设计

**一、痛点排序靠数据，不靠直觉。** 先写 `scripts/context_budget.py` 量化，才发现两件事：

- **token 换算率必须实测标定。** 按英文经验值（4 字符/token）估中文会**低估 3 倍**。由 `/context` 的两个实测点解出 CJK ≈ 1.03 token/字、非 CJK ≈ 0.59 token/字。这个误差本身就是「拍脑袋精简」的典型翻车点——开轮时我第一次估算就错了 3 倍。
- **常驻 token 已不是痛点**（round51 让 playbooks 退出常驻后只剩宪法 + 项目 `CLAUDE.md`）。真痛点是**单次加载密度**与**只增不减的棘轮**。

**二、blog 六个 shift 对到本仓，最大头是 shift 4（Repetition → Concision），不是「删」。** 而且这块重复**文档自己承认过**：

- `sync-project-config` 写着「与 bootstrap Step 3.3.7 **同一份，改动时两处同步**」「逻辑**等同** bootstrap 的 Step 3.5」；
- `commit` 第 4 步写着「细节以 `/review-loop` 为**单一真源**」，紧接着复述了 700 字符。

review 机制的同一套判据原本写在 **6 个地方**。

**三、精简的正解主要是「分层」和「去重」，不是删。** 三板斧（人类拍板的力度档）：

| # | 判据 | 性质 |
| --- | --- | --- |
| A1 | 已有单一真源的重复表述 → 删，留指针 | 零信息损失 |
| A2 | 成组同向细则 → 上提为一句判断原则 | 有意的信息压缩（blog shift 1） |
| A3 | 事故 WHY 的**过程叙事** → 压成结论一句 | 结论保留，只删叙事 |
| A4 | 失效引用 | 零损失 |
| A5 | Agent 已从工具 schema 得知的重复 | 零损失 |

**明确不做 ablation 删除**（不因「Claude 5 不被告知也会做对」就整条删掉含 WHY 的规则）——缺乏实证，误删要靠下次踩坑才发现。

**四、只允许「搬走」不允许「蒸发」。** 删除型 diff 的麻烦是「少了什么是看不见的」，`git diff` 告诉不了你那条信息是搬走了还是没了。两道护栏：① `docs/52-*/SLIM-LEDGER.md` 每条删减记三列（**删了什么 / 依据哪条判据 / 现在从哪读得到**）；② `context_budget.py check-refs` 机械校验所有指针可达——**指针指不到东西 = 那条信息真的没了**。

### 开发内容概括

| 阶段 | 产物 |
| --- | --- |
| 0 | `scripts/context_budget.py`（`measure` / `delta --since` / `check-refs`）+ 41 项单测（TDD 正序） |
| 1 | 抽 `templates/MECHANICS.md`，消灭 bootstrap 与 sync 之间已承认的双写 |
| 2 | review 链路收敛到 `/review-loop` 单一真源 |
| 3 | `GLOBAL_AGENTS.md` 三板斧 |
| 4 | `finish` / `routine-docs` / `rebase` 三板斧 + 拆 `references/` |
| 5 | **新增 `/routine-slim`**——把本轮实操出来的判据固化成每周定时任务 |

**量化结果**（被精简的 9 个文件）：

| 文件 | 前 | 后 |
| --- | ---: | ---: |
| `skills/sync-project-config/SKILL.md` | 16,501 | 6,817 |
| `skills/routine-docs/SKILL.md` | 14,311 | 9,818 |
| `skills/bootstrap/SKILL.md` | 11,521 | 4,788 |
| `skills/review-loop/SKILL.md` | 10,731 | 7,415 |
| `skills/finish/SKILL.md` | 10,476 | 6,151 |
| `GLOBAL_AGENTS.md` | 9,922 | 6,327 |
| `skills/rebase/SKILL.md` | 4,821 | 4,600 |
| `skills/commit/SKILL.md` | 2,869 | 2,311 |
| `CLAUDE.md` | 5,042 | 5,230（净增：安全边界段扩为两条 routine） |
| **合计** | **86,194** | **53,457（-38%）** |

其中 **10,618 字符是搬到** `templates/MECHANICS.md` + 两份 `references/`（内容一字未少，改为按需读），**真正删除约 22,100 字符**。

**常驻上下文**（每会话每项目）：14,964 → 11,557 字符，**11,610 → 8,851 token（-24%）**。

**全仓指令面**：162,562 → 147,473 字符（-9.3%）——这个数含**新增的** `/routine-slim`（7,030）。不含新功能的话是 -13.6%。降幅被稀释是因为 `playbooks/*.md`（52,681，占当前总量 36%）按人类决定本轮未碰。

**单次加载的实际改善**（更贴近痛点）：`/sync-project-config` 16,501 → 6,817（真要写文件时再 +5,478）；`/finish` 10,476 → 6,151（worktree 轮再 +2,409）。

### 额外产物

- `docs/52-*/SLIM-LEDGER.md` —— 三列账本，**本轮人工 review 的主要对象**
- `docs/52-*/REVIEW.md` —— 每阶段的自审 finding 与处置
- `docs/52-*/BASELINE.md` —— 开轮基线量化
- `docs/52-*/test_context_budget.py` —— 41 项零依赖单测
- `scripts/.gitignore` / `docs/52-*/.gitignore` —— 本仓首次出现 Python 字节码缓存

## 局限性

1. **⚠ 本轮全部 commit 未经独立 context review。** 本 session 被显式约束「不得调用 Agent 工具」，`/review-loop` 的首选路径不可用，按其降级链退到**主会话结构化自审**。开发对话的先入之见在场，「实际写的和想的不一样」这类问题最容易漏。**而本轮改的几乎全是指令规则文件（门禁自身的规则）——人工 review 是唯一的独立视角。** 请以 `SLIM-LEDGER.md` 为主要核对对象。
2. **`check-refs` 抓不到章节锚点失效。** 别的 skill 按**章节名**引用宪法（`finish` 引「总结」部分、`commit` 引「git 规则」、`review-loop` 引 TDD 章）。改标题会让这些指针失效，而机械检查只查文件路径。本轮四处引用已逐条人工核对仍可定位，但这类风险没有自动兜底。
3. **`/routine-slim` 从未真正跑过。** 阈值 15%、「一次只动 1–3 个文件」都是拍的，没有实证。**上线前必须先 `--dry-run` 并由人过目**（`playbooks/cloud-routine.md` §5 已立此规；`/routine-docs` 上线前那次 dry-run 当场改掉两条规则）。
4. **`templates/MECHANICS.md` 不在自动精简覆盖面内。** `templates/` 整体在 `/routine-slim` 黑名单里（它承载会被真实执行的项目配置），故这份 5,478 字符的新文档从此只能人工维护。
5. **`playbooks/*.md`（52,681，占指令面 36%）本轮未碰**，按人类开轮时的决定交给 routine 逐周做。同理未动的还有 `devtree` / `start` / `quick` / `backlog` / `pybump` / `paper-read` 六个 skill——它们没有跨文件重复这个大头。
6. **精简的正确性无法用单测断言。**「规则删了之后 Agent 还会不会做对」不是可断言命题。人类明确否掉了机械断言清单，故最后一道闸就是人工 review。
7. **合入后需重跑 `bash install.sh`**（新增 `skills/routine-slim/` 与 `scripts/context_budget.py`，二者都是逐条软链）。本轮未实跑——在 worktree 里跑会把 `~/.claude` 整体重指到未合入的分支。

## 后续 TODO

1. **`/routine-slim --dry-run` 人过目并校准阈值**（对应局限 3）——这是上线前的硬前置。
2. **注册 cron**：在 claude.ai 建 routine，周日 01:00 UTC，`sources` 挂本仓（prompt 模板在 SKILL.md 末节）。
3. **让 routine 首批处理 `playbooks/*.md` 与六个小 skill**（对应局限 5）——既是真实收益，也是判据质量的试验场。
4. **考虑给 `check-refs` 加章节锚点检查**（对应局限 2）：扫「`X.md`『Y』段」这类引用，断言 `Y` 仍是该文件的标题之一。
5. **人工跑一次跨模型 review**（对应局限 1）：本轮改的是门禁自身的规则，且未经独立 context 把关，值得一次真正独立的第二意见。
6. **观察一到两个月的 `delta` 曲线**，验证「有涨有落」是否真的成立——如果 routine 每周都触发但降幅很小，说明阈值或判据要调。

## 可沉淀项

本仓**就是** claude-code-global，按 `/finish` Step 3.3 的自指守卫，跨项目候选改为建议走本地 `/backlog`，不跨仓库 file。三条候选（**未自动建 issue，供人决定**）：

1. **`context_budget.py` 的 token 标定方法可复用**：「按英文经验值估中文低 3 倍」不止影响本仓——任何要估 context 成本的中文项目都会撞上。可考虑写进 `playbooks/` 某处，或做成通用小工具。
2. **「只允许搬走不允许蒸发」的三列账本**是删除型 PR 的通用护栏，不限于精简场景（重构、去依赖、删死代码都适用）。值得考虑写进宪法或 `/commit`。
3. **`check-refs` 的「精确白名单而非启发式」教训**：首跑 72 条误报几乎全是把消费方项目路径当本仓路径。任何做静态引用检查的工具都会遇到这个取舍——**误报会让人不再看这个检查，等于白做**。
