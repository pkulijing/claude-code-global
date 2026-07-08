# PLAN — review-loop 收敛闸重构

> 对应 [PROMPT.md](./PROMPT.md) / [#24](https://github.com/pkulijing/claude-code-global/issues/24)

## 决策（已与人类确认）

1. **codex 分层**：日常 commit 默认走 CC 自带 `/code-review`（快、自带 verification step 过滤误报）；只有 diff 命中「复杂 / 并发 / 难复现」特征时才**自动升级**引 codex 做一次性独立第二意见。
2. **运行验证闸**：每轮修复后，有对应测试**必跑、失败阻断**；被改代码是编排器 / facade（rules §3.7）却无 happy-path integration test → **先补一条再放行**。
3. **置信过滤闸**：对齐 anthropic 官方 code-review plugin——只报「附 file:line 源码证据 + 高置信真会在生产触发」的 correctness 问题；pre-existing / pedantic / linter 域 / 推测式 corner case 一律不报。

## 核心变化：收敛闸从「reviewer 说 clean」→ 三要素并闸

**旧闸**（round 45/46）：`codex review → 修 → 复审`，收敛 = codex 报无「正确性/逻辑/安全」问题。缺陷：无置信过滤（任何编得出的 corner case 都过闸 → 慢+挑刺）、无运行验证（codex read-only 只读不跑 → 基础功能审废无人知）、codex 每 commit 无限迭代（用法层级错）。

**新闸**：一轮 review 收敛，当且仅当三者同时成立——

- **(A) 运行验证通过**：受影响测试全绿 + happy-path 主流程跑通（编排器无测则先补）；
- **(B) 无高置信 correctness finding**：reviewer 按置信闸过滤后，无「附证据、高置信真会出错」的正确性/逻辑/安全问题；
- **(C) 已定前提未被重复质疑**：Step 0 清单外的新问题才计入。

三者任一不满足 → 未收敛，进修复迭代。**关键顺序**：验证闸(A)在置信闸(B)**之前**跑——先确认「基础功能没被上一轮修废」，再谈「还有没有新问题」。这直接堵死症状二。

## 分层 reviewer 选择（Step 3 改造）

原 Step 3 只判「有没有独立 reviewer」。新增一层「**选哪个 reviewer**」，在「琐碎跳过」之后、「独立性判定」之前：

- **默认档 = CC `/code-review`**：多数 commit 走它。它本身是「多 agent 并行 + verification step 过滤误报 + 默认只查 correctness」，快且低噪。
- **升级档 = codex 独立 review**：diff 命中以下**任一复杂特征**时自动升级（启发式，reviewer 自己判，写进 skill 供人类调）：
  - 多线程 / 并发 / 异步生命周期（线程、`asyncio`、锁、跨线程队列、`join`/`cancel`）；
  - 跨进程 / 网络 / 重试 / 幂等 / 部分失败 / 回滚路径；
  - 状态机 / 竞态 / 排序假设 / 资源生命周期（文件/socket/channel 的开关配对）；
  - 难以用测试复现、或改动横跨 3+ 模块的编排装配。
- **升级档仍受独立性判定约束**：只有「diff 全由 CC 写 + codex 可用」时 codex 才算独立（原 Step 3 逻辑保留）；否则降级本会话自审并标注。
- **人类可显式覆盖**：手动 `/review-loop` 时可指示强制走 codex（复杂改动想要第二意见）。

> 效果：日常快（CC 单次）、重活准（codex 上跨模型），不再让每个琐碎 commit 背一次 codex 全量迭代——正面回应「变慢」。

## 置信过滤闸（注入 reviewer PROMPT + 分诊）

两处落地：

1. **codex PROMPT 第 2 段**（攻击面清单）后追加「**只报高置信 + 证据**」硬约束：每条 finding 必须给出 `file:line` 源码证据、且高置信「真会在生产触发」；**明令不报**：pre-existing（非本次 diff 引入）、pedantic 风格、linter/type-check 能抓的、「看着像 bug 但你没有证据证明会触发」的推测式 corner case。
2. **Step 6 分诊**：收敛判据从「有无正确性/逻辑/安全问题」收紧为「有无**高置信** correctness finding」。低置信 / 无证据 / pedantic 一律不阻断（顺手能改可改，不强制、不计入迭代）。CC `/code-review` 档天然带此过滤，无需额外注入。

## 运行验证闸（Step 6 修复后新增子步）

Step 6 每轮「修复 → 复审」之间插入**验证子步**（呼应 `/verify` skill、rules §3.7、宪法 TDD 章）：

1. 探测受影响测试并跑（沿用 `/commit` 的项目类型探测：`uv run pytest` / `npm test` / `cargo test` / `go test`）。**失败 → 未收敛**，停下修（走 TDD 正序）。
2. 被改代码含**编排器 / facade**（`__init__` 收外部资源 + 有 `run`/`execute`/`process` 主入口 + 调 3+ 模块，见 rules §3.7 启发式）却无 happy-path integration test → **先补一条**（最小 fixture 端到端跑主入口、只验「跑通不报错」）再继续。
3. **无测试框架 / 纯文档 / 指令规则文件**（本 skill 自身、宪法等无运行时面）→ 验证闸 N/A，跳过本子步（但这类仍走置信闸 review）。

> 与旧 skill 已有的「回归全量」段合并去重：旧段只在「走 TDD 正序的代码类修复」后要求重跑，现提升为**每轮独立验证子步**、且补齐「编排器无测先补」。

## 具体改动清单

### 1. `skills/review-loop/SKILL.md`（主改）

- **Step 2 后 / Step 3 前**：新增「Step 2.5：选 reviewer 档位」（默认 CC / 升级 codex 的启发式清单）。
- **Step 3**：措辞对齐——独立性判定只在「升级档」内生效（CC 档不涉及跨模型独立性问题）。
- **Step 4 PROMPT 三段式**：第 2 段后加「高置信 + 证据」硬约束段。
- **Step 4 新增「默认档：CC /code-review」小节**：说明何时直接调 `/code-review`（单次、`--fix` 不用，手动分诊）而非 codex。
- **Step 6**：
  - 收敛判据「有无正确性问题」→「有无**高置信** correctness finding」；
  - 「修复 → 复审」间插入**运行验证子步**（测试必跑 + 编排器补 happy-path）；
  - 与旧「回归全量」段合并去重。
- **「为什么存在」段**：补一句「收敛靠『运行验证 + 高置信过滤』，不是靠 reviewer 挑不出为止」，点明反 nitpick / 反审废基础功能。

### 2. `GLOBAL_AGENTS.md`「独立模型 review」小节（同步措辞）

- **机制**行（line 84）：把「迭代到无该修的问题（clean）才放行」改为「迭代到**运行验证通过 + 无高置信 correctness 问题**才放行」；补「日常默认 CC `/code-review`、复杂/并发/难复现 diff 才升级 codex」的分层。
- 保留 TDD 正序、独立性判定、降级不跳过三条不变。
- **核心开发模式**段（line 36/51）：`/review-loop` 一句话描述同步为「运行验证 + 高置信过滤迭代至 clean」。

### 3. `skills/commit/SKILL.md`（轻量同步）

- 第 4 步对 `/review-loop` 的转述同步「分层 + 运行验证」措辞（单一真源仍是 review-loop，此处只跟措辞）。

## 本轮是否走 review-loop 自身（自举处理）

本轮改的是**门禁规则文件**（skill + 宪法），属「绝不自动跳过 review」类；但 review 规则类文档问题空间近乎无穷、易无限烧 token（旧 skill 自举踩过近 20 轮）。故本轮 **review 由人类把关**（即你现在做的 PLAN review + commit 前你亲自看 diff），**不自动跑 review-loop 自审自举**——这本身就是新 skill「每 3 轮硬闸、规则文档人类判」精神的体现。commit 时若 `/review-loop` 被自动触发，会命中「指令规则文件不跳过」但可由你手动判定收敛。

## 验证方式（本轮无代码运行时面）

本轮交付是 Markdown 指令文件，无可运行的代码单元，故：

- **一致性自查**：改完通读三个文件，确认 review-loop / commit / 宪法三处对「收敛闸 = 运行验证 + 高置信过滤 + 分层 reviewer」的表述**互不矛盾、无 drift**；
- **术语对齐**：确认新引入的「高置信 finding」「运行验证闸」「reviewer 档位」在三处用词统一；
- **不破坏现有约束**：TDD 正序、每 3 轮硬闸、降级路径、安全（PROMPT 走临时文件 stdin）等原有硬规则原样保留。

## 交付物

- 重构后 `skills/review-loop/SKILL.md`
- 同步后 `GLOBAL_AGENTS.md`、`skills/commit/SKILL.md`
- `docs/47-review-loop收敛闸重构/SUMMARY.md`
- 收尾 `/finish`：`Closes #24`
