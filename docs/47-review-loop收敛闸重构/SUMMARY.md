# SUMMARY — review-loop 收敛闸重构

> 对应 [PROMPT.md](./PROMPT.md) / [PLAN.md](./PLAN.md) / [#24](https://github.com/pkulijing/claude-code-global/issues/24)

## 开发项背景

round 45/46 落地 `/review-loop`（commit 前自动引入独立第二模型 codex review 当前 diff、迭代至 clean）后，实战暴露两个症状：

1. **开发变慢**：review 总在犄角旮旯挑无关紧要的 corner case，每个小 commit 都背一次全量 codex 迭代。
2. **review 效果差**：某项目连审多轮，最后出来的代码**基础功能都是废的**。

调研头部意见领袖（Karpathy / Addy Osmani）与 GitHub top review skill / CC 自带 `/code-review` 后定位：问题不在「该不该用 codex」（跨模型独立视角的价值——issue 原始硬实证 grpc.aio 迁线程 codex 补 3 个 P1——依然成立），而在 **review-loop 的收敛判据设计错了**。

## 实现方案

### 关键设计：收敛闸从「reviewer 说 clean」→ 三要素并闸

旧闸收敛信号是「codex 报无正确性问题」，两个致命缺陷：

- **无运行验证**：codex 跑 `read-only` 只读代码、不跑代码，全程无任何一步真正运行 → 基础功能被某次「外科手术式修复」改废也无人发现（症状二，设计缺陷非运气）。
- **无置信过滤**：判据「是否真会出错」无置信阈值，codex 问题空间近乎无穷、任何编得出的 corner case 都过闸（症状一）。

新收敛闸 = 三者同时成立：

- **(A) 运行验证通过**：受影响测试全绿 + happy-path 主流程跑通（编排器无 happy-path test 先补一条）。**硬前置、排在 (B) 之前**——先确认基础功能没被上一轮修废。呼应 Karpathy「测试过了才算修好」、Osmani「testing 是最大分水岭」、本仓 `rules/python.md` §3.7。
- **(B) 无高置信 correctness finding**：对齐 anthropic 官方 code-review plugin 的 ≥80 置信阈值——只认「附 `file:line` 证据 + 高置信真会在生产触发」的问题，pre-existing / pedantic / linter 域 / 推测式 corner case 一律不阻断。
- **(C) 已定前提未被重复质疑**：沿用旧逻辑。

### 关键设计：分层 reviewer（治「慢」的另一半）

不再每 commit 都上跨模型 codex 全量迭代：

- **默认档 = CC 自带 `/code-review`**（多数 commit）：多 agent 并行 + verification step 过滤误报 + 默认只查 correctness，快且低噪。
- **升级档 = codex 独立 review**：仅 diff 命中「并发 / 多线程 / 跨进程重试 / 状态机 / 难复现 / 跨 3+ 模块编排」复杂特征才自动升级（正是「同一个脑子难自审」的高价值场景，也是 issue 原始硬实证的场景）。
- **人类覆盖**：`/review-loop --codex` 强制升级档 / `--cc` 强制默认档。
- **降级链更新**：升级档 codex 不可用 → 回退默认档 CC `/code-review`；连它都不可用才降级本会话自审。优先级：**codex 独立 review > CC `/code-review` > 本会话自审 > 不 review**。

### 开发内容概括

改 3 个门禁规则文件（均属「绝不自动跳过 review」类）：

1. **`skills/review-loop/SKILL.md`**（主改）：
   - 「为什么存在」+「loop 是什么」段重写收敛哲学（三要素并闸 + 分层）；
   - 新增 **Step 2.5 选 reviewer 档位**（默认 CC / 升级 codex 启发式清单 + `--codex`/`--cc` 覆盖）；
   - Step 3 独立性判定收窄到「仅升级档」；
   - 新增 **Step 4A**（CC 默认档）、原 Step 4 改为 **Step 4B**（codex 升级档），PROMPT 三段式 → 四段式（新增**置信闸**第 3 段）；
   - Step 5 降级改为「最后兜底」（连 CC `/code-review` 都不可用才落）；
   - **Step 6 重构**为 6.1 分诊（闸 B）→ 6.2 修复（TDD 正序）→ **6.3 运行验证子步（闸 A，本轮核心新增）** → 6.4 复审收敛。
2. **`GLOBAL_AGENTS.md`**「独立模型 review」小节 + 核心开发模式两处：同步分层 / 运行验证 / 置信过滤 / 降级链措辞。
3. **`skills/commit/SKILL.md`** 第 4 步：跟措辞（单一真源仍是 review-loop）。

### 额外产物

无独立测试 / 脚本（交付为 Markdown 指令文件）。做了跨文件一致性自查：术语对齐（高置信 / 运行验证 / code-review 三文件全覆盖）、无旧优先级链残留、原有硬规则（每 3 轮闸口、防假绿、TDD 正序、临时文件走 stdin 防命令注入、read-only 安全边界）完整保留。

## 局限性

- **启发式判档靠 CC 自估**：「diff 是否命中复杂特征」由 CC 每次自己判，可能漏判（把并发 diff 误当简单）。已加两条缓冲：判定拿不准时「偏向升级」的明确指令 + `--codex` 手动逃生舱。但根本上仍是模型判断、非硬检测。
- **置信闸对 codex 是软约束**：PROMPT 指令 codex「只报高置信」依赖模型遵守；6.1 分诊再兜一层（丢弃无 `file:line` 证据项）作为硬后置过滤，但非零漏网。
- **CC `/code-review` 的前提清单注入是间接的**：升级档经 PROMPT 第 4 段注入已定前提，默认档无独立进程可注入、只能在 6.1 分诊时应用——两档前提传递路径不对称。
- **本轮自身未跑独立 review-loop**：改的是门禁规则文档（问题空间近乎无穷、易无限烧 token），本轮 review 由人类把关（PLAN review + commit 前看 diff），未自动跑 codex 自举——这本身是新 skill「规则文档人类判」精神的体现。

## 后续 TODO

- **补齐「codex 写的代码调起 CC 做独立 review」入口**（issue #24 原始遗留 TODO，本轮未动）：当前 codex 写的 diff 升级档不成立时只能回退 CC `/code-review`（同端非跨模型），真正的跨模型独立仍缺。
- **观察分层判档的实战命中率**：跑一段时间后回看「该升级 codex 却走了 CC 默认档」的漏判案例，据此细化 Step 2.5 启发式清单，或考虑加轻量硬信号（如 diff 命中 `asyncio` / `threading` import 自动升级）。
- **可选：`/code-review` finding 的结构化提取**：当前 Step 4A 取 CC `/code-review` 的 finding 靠自然语言，若未来 `/code-review` 提供机读输出（如 severity JSON），可让 6.1 分诊更确定性。

## 可沉淀项

本轮改动本身就是对 claude-code-global 门禁流程的沉淀（已落 `/review-loop` + 宪法 + `/commit`、关联 #24），故无需另提跨仓库 issue。反思过程另有两点通用认知，但均已内化进本轮改动、无独立落点：

- **「AI review loop 的收敛信号应是『运行验证 + 高置信过滤』而非『reviewer 挑不出为止』」** 是跨项目通用的 review 哲学（Karpathy / Osmani / anthropic 官方 code-review plugin 三方印证）——已写进本轮 review-loop 与宪法，无需再沉淀。
- **CC 自带 `/code-review` 的 verification step 是对付 self-review 误报的现成机制**——已作为默认档接入本轮 skill，无需另建资产。

综上：**暂无需要额外 file 的跨项目沉淀项**（Step 3 反思结论一致）。
