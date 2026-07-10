# 实现计划：/review-loop 去 codex + 永远委派 + 两档

## 一、目标

一句话：**把 `/review-loop` 的分层轴从「reviewer 身份」换成「永远委派子 agent + 两档」**，顺带把 codex-as-reviewer 的全部描述从仓库四处拆除。

改完后 `/review-loop` 的心智模型应当能一句话说清：

> 委派一个子 agent 对当前工作树 diff 跑 `/code-review <档位>`（默认 sonnet × medium，硬 diff 用 opus × high），主会话只收 finding 列表，按三要素并闸迭代到 clean。

## 二、关键设计决策

前置事实全部来自 CLI 2.1.206 二进制，详见 `PROMPT.md`「问题二」。**其中两条推翻了本 PLAN 的早期版本**：`/code-review` 的 angle 是 inline 的（无 worker 扇出）；Opus 全档位 `no verify`、且 `medium` 与 `high` 同为 8 angle、成本几乎相同。

| #   | 决策                                                          | 理由                                                                                                                                                    |
| --- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | reviewer 唯一化为 CC `/code-review`                           | 判定链过长、codex 档实际触发率近零、维护面外溢四个文件                                                                                                  |
| D2  | **硬规则一：永远显式传档位**                                  | 裸调继承 session effort（`l ?? g_(t)`），ultracode session 下即 xhigh（10 angle + sweep），是 token 惨案的直接成因                                      |
| D3  | **硬规则二：永远委派子 agent 跑 review，重档也不例外**        | angle 是 inline 的 → 主会话直调会把 8–10 轮文件阅读永久写进主对话历史、逐轮复利。委派把它关在子 agent 里，主会话只收 finding                            |
| D4  | **硬规则三：合法组合只有 `sonnet × medium` 与 `opus × high`** | `/code-review` 无模型参数（flag 白名单 `["fix","comment"]`，模型 = `options.mainLoopModel`），唯一可自动化的换模型途径就是委派给指定 `model` 的子 agent |
| D5  | **删除 `low` 档**（早期版本的「轻档」）                       | `low` 省的是与 diff 规模成正比的部分，小 diff 上本就小；且 Sonnet `medium` 自带 1-vote verify 而 `low` 没有 —— 误报引发的无效修复轮才是循环的成本大头   |
| D6  | 复审轮**不降档**                                              | 沿用首轮档位，只把委派 prompt 的任务收窄；收敛由 2 轮硬闸兜底，不需要第二条规则                                                                         |
| D7  | 委派 prompt 必须携带「已定设计前提」摘要                      | 子 agent 无本轮对话上下文，否则会质疑人类已拍板的决策、制造假 finding                                                                                   |
| D8  | 复杂特征清单原样保留                                          | 它本来就是「哪些 diff 值得多花钱」的判据，与升级目标是 codex 还是 opus×high 无关                                                                        |
| D9  | 宪法硬实证段**降格为「已知局限」保留**                        | CC `/code-review` 仍是同模型自审，对并发 / 难复现有已知盲区。诚实声明边界，而非假装问题不存在                                                           |
| D10 | Step 0「已定前提清单」**并进 6.1 分诊**                       | 失去 codex PROMPT 注入通道后只剩一条分诊规则，不值一个章节                                                                                              |
| D11 | 人工闸口由**每 3 轮收紧为每 2 轮**                            | 三轮自动迭代跑下来人要等太久；闸口的价值在「早点让人判断值不值得继续」，两轮已足够暴露是否在振荡 / 发散                                                 |

### 禁止组合及其硬理由（写进 SKILL.md，防未来「顺手升档」踩坑）

| 组合                 | 为什么禁                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------------------------ |
| `sonnet × high\|max` | `finderBudgetHint` 只在 `claude-sonnet-5` 的 high/xhigh/max 开启 → 扇出 2–8 个 finder 子 agent，比 Opus 还贵 |
| `opus × medium`      | 与 `opus × high` 同为 8 angle、同价，findings 上限却更低 —— 被严格支配                                       |
| 任意 `× xhigh`       | 10 angle + sweep，本次惨案的规格；且它不是 `/code-review` 的合法入参，只能靠继承拿到（D2 已封死）            |

## 三、新 SKILL.md 骨架

步骤从 9 段（含 2.5 / 4A / 4B 三个畸形编号）压到 6 段，编号连续：

```
frontmatter（description 重写）
## 为什么存在              ← 保留「收敛靠运行验证+置信过滤」；删跨模型独立性论证；新增「成本」病根
## loop 是什么             ← 三要素并闸判据（A/B/C）不变
## Step 1：确认有变更       ← 原样
## Step 2：琐碎改动跳过判定  ← 原样（配置 / 指令文件不跳）
## Step 3：选档（三条硬规则 + 两档表 + 禁止组合表） ← 新写（吸收原 Step 2.5 的复杂特征清单）
## Step 4：委派子 agent 跑 review                   ← 由原 Step 4A 扩写
## Step 5：降级链（委派失败 / /code-review 不可用）  ← 由原 Step 5 改写
## Step 6：分诊 + 运行验证 + 迭代收敛
   6.1 分诊（含「已定前提」分诊规则，吸收原 Step 0）
   6.2 自动修复（TDD 正序）    ← 原样
   6.3 运行验证子步（闸 A）    ← 原样
   6.4 复审收敛（2 轮硬闸；不降档）
## 明确不做
```

**净删除**：原 Step 0（独立章节）、Step 2.5、Step 3（独立性判定）、Step 4B（含 PROMPT 四段式、stdin 注入安全硬规则、`-c` 保险、输出噪音清单、软防护边界声明）、`--codex` / `--cc` flag。粗估砍掉 ~55% 篇幅。

### Step 3 + Step 4 + Step 5 措辞草案

````markdown
## Step 3：选档

**硬规则一：调 `/code-review` 必须显式带档位。** 裸调会让它继承当前 session 的 effort
——ultracode / xhigh session 下，一个 5 行的 diff 也按 xhigh（10 个 angle + sweep）审，
成本与 diff 规模完全脱钩。显式传档把 review 成本钉死在本 skill 手里。

**硬规则二：review 永远在子 agent 里跑，主会话不直接跑 —— 重档也不例外。**
`/code-review` 的各个 review angle 是 **inline** 的，跑在调用方的 context 里：主会话直调
会把 8–10 轮文件阅读永久写进主对话历史，之后每一轮都要重发。委派后主会话只收一份
finding 列表。代价是子 agent 一份固定的 standing context（约 5 万 token 量级，绝大部分
是可缓存 input），远小于主 context 被撑大的复利。

**硬规则三：只有两个合法的「模型 × 档位」组合。**

| 档       | 委派模型 | 命令                  | 触发                   |
| -------- | -------- | --------------------- | ---------------------- |
| **默认** | `sonnet` | `/code-review medium` | 一切需要 review 的改动 |
| **重**   | `opus`   | `/code-review high`   | 命中下列任一复杂特征   |

禁止组合（别顺手「升档」踩进去）：

- `sonnet` + `high`/`max` → 打开 finder 扇出（2–8 个 finder 子 agent），比 Opus 还贵；
- `opus` + `medium` → 与 `opus` + `high` 同为 8 个 angle、同价，findings 上限却更低；
- 任何档位 + `xhigh` → 只能靠继承 session effort 拿到，硬规则一已封死。

**升重档的复杂特征**（这些正是「审浅了会漏真 bug」的场景）：

- 并发 / 多线程 / 异步生命周期：线程、asyncio、锁、跨线程队列、join / cancel / 优雅停；
- 跨进程 / 网络 / 容错：重试 / 幂等 / 部分失败 / 回滚 / 超时 / 降级路径；
- 状态机 / 竞态：排序假设 / 陈旧状态 / 重入 / 资源生命周期（文件 / socket 开关配对）；
- 难以用测试复现，或改动横跨 3+ 模块的编排装配。

拿不准时**偏向升重档** —— 漏判一个并发 diff 的代价，大于多花一次 opus × high。

**没有第三档**：`low` 只省「与 diff 规模成正比」的那部分推理（小 diff 上本就小），
却丢掉 Sonnet `medium` 自带的 1-vote verify。而本 loop 真正的成本大头是**误报引发的
无效修复轮**，不是 review 本身。小改动该跳过的已在 Step 2 跳过了；没跳过的
（配置、指令规则文件）每行都重，不该降规格。

## Step 4：委派子 agent 跑 review

```
Agent(
  subagent_type: "general-purpose",
  model: "sonnet" | "opus",        // 按 Step 3 选档
  run_in_background: false,        // 必须同步：拿到 finding 才能往下走
  prompt: """
    对当前工作树的 diff 跑 `/code-review medium`（或 high），不带 --fix / --comment。
    原样返回它输出的 finding 列表（含每条的 file:line 与严重度），不要自行修改任何文件。

    本轮已定的设计前提（不要把对这些的质疑当作 finding）：
    - <逐条列出人类已拍板的决策>
  """
)
```

三条要点：

- **`run_in_background: false`**：默认后台跑，本 loop 需要 finding 才能继续，必须同步。
- **不带 `--fix`**：本 skill 要自己走 Step 6 的分诊 + TDD 正序修复 + 运行验证闸；
  `--fix` 会绕过验证闸直接改。只取 finding 列表。
- **不带 `--comment`**：本地迭代，不发 PR 评论。
- **必须带「已定设计前提」摘要**（D7）：子 agent 没有本轮对话的上下文，不告诉它哪些是
  已拍板的决策，它就会去质疑，产出一堆假 finding，白烧 2 轮闸口的额度。

## Step 5：降级链

优先级：**委派子 agent 跑 `/code-review` > 主会话直跑 `/code-review <档位>` > 本会话自审 > 不 review（禁止）**。

- 委派失败（子 agent 起不来 / 跑不起 `/code-review` / 返回的不是 finding 列表）→
  退回主会话直跑同档位 `/code-review`，并**告知用户「本次 review 未走委派，主 context 会
  因此增大」**。
- `/code-review` 本身不可用（命令缺失 / 报错）→ 停下告知用户
  「**本次降级为本会话自审、未经把关**」再继续。
- **绝不静默跳过**。
````

## 四、逐文件改动清单

### 1. `skills/review-loop/SKILL.md`（主体，~194 行 → 预计 ~95 行）

- frontmatter `description` 重写：去掉 codex / 升级档 / `--codex` / `--cc`，改述「委派 + 两档 + 三要素并闸」。
- 「为什么存在」：删第 3 段（分层 reviewer）、第 4 段（独立性要害）、第 5 段（怎么调 codex）；新增一段讲**成本病根**（inline angle 污染主 context + 档位继承），点明三条硬规则的由来。
- 「loop 是什么」：判据 (C) 描述里的「独立模型报的问题」改为「reviewer 报的问题」。
- **改掉一处旧文案的事实错误**：现存 SKILL.md 称 CC `/code-review`「多 agent 并行 + 独立 verification step 过滤误报」——在 Opus 上是假的（全档位 `no verify`，且 angle 是 inline 的）。改为按模型族如实描述：Sonnet 档才有 1-vote verify，这也是默认档选 Sonnet 的理由之一。
- 删 Step 0 章节，其语义并入 6.1。
- Step 2.5 → 新 Step 3（见上草案）。
- Step 3（独立性判定）→ 整节删除。
- Step 4A → 新 Step 4（见上草案）：委派 + `run_in_background: false` + 已定前提摘要；`--fix` / `--comment` 均不带的既有理由保留。
- Step 4B → 整节删除。
- Step 5 → 改写为三级降级链（见上草案）。
- 6.1 → 增加「已定前提」分诊规则（三条分诊出口：高置信 correctness / 命中已定前提 / 低置信噪音）。
- 6.4 → 人工闸口由**每 3 轮收紧为每 2 轮**（D11）；**不加**复审降档规则（D6）。
- 「明确不做」→ 删「不做文件集隔离 / stash」条（codex 语境的产物），其余保留。

### 2. `GLOBAL_AGENTS.md`

- **§「独立模型 review（commit 前自动跑）」→ 改标题为「提交前 review（自动跑）」**。
- 硬实证段 → 重写为「已知局限」：保留 grpc.aio 实证，但改述为「CC `/code-review` 是同模型自审，对并发 / 难复现改动有已知盲区；需要跨模型第二意见时人工手动引入，本流程不自动做」。
- 「不是每个 commit 都值得上跨模型 codex」→ 改为「不是每个 commit 都值得上强模型 + high effort」。
- 「机制」句 → 改述为「委派子 agent 跑 `/code-review`，默认 sonnet × medium，硬 diff 升 opus × high」；收敛判据两条原样。
- 「独立」定义整条删除 → 替换为一条「永远显式传档位 + 永远委派 + 组合白名单」的硬规则。
- 「降级不跳过」→ 优先级链改为 `委派 /code-review > 主会话 /code-review > 本会话自审 > 不 review`。
- 人工闸口段 → **3 轮改 2 轮**（D11）；琐碎可跳过 → 原样不动。
- 第 36 行、第 51 行内联描述 → 同步。

### 3. `skills/commit/SKILL.md`

- 第 4 步整段重写：删掉 codex 升级 / 独立性 / 回退链三层描述，改为「调 `/review-loop`，它委派子 agent 跑 `/code-review`（默认 sonnet × medium，硬 diff 升 opus × high）并迭代到 clean」。其余（放在 lint 之前的理由、2 轮闸口、留痕）保留。
- **不动**第 9 步的 `Co-authored-by` 身份选择（双轨部署语义）。

### 4. `README.md`

- 第 87 行导语、第 95 行 `/commit` 表格行、第 96 行 `/review-loop` 表格行、第 198 行工作流串 —— 四处同步，删「升级引 codex 独立 review」「`--codex`/`--cc`」等。

## 五、测试与验收

**本轮改的是指令 / 文档本身，无可运行代码单元** —— 按宪法 TDD 章「例外」与 `/review-loop` 6.2 分流，属「改的就是指令 / 文档本身」→ 无红测试可写，直接改；6.3 闸 A 判 **N/A**。

代之以四条**可机械核验**的验收：

1. **codex-as-reviewer 清零**：

   ```bash
   grep -rIn --exclude-dir=.git --exclude-dir=docs -i 'codex exec review\|独立模型\|跨模型\|升级档\|--codex' .
   # 期望：无输出
   ```

2. **双轨部署语义无损**（回归防误伤）——改动前后各跑一次，比对差异应为空：

   ```bash
   grep -rIcn --exclude-dir=.git --exclude-dir=docs -i codex install.sh codex.config.base.toml \
     scheduler/install.sh scripts/auto-update.sh CLAUDE.md rules/*.md
   # 期望：各文件计数与改动前完全一致
   ```

3. **无裸调 `/code-review`**：全仓搜 `/code-review` 的每一处出现，确认要么带档位（`medium`/`high`），要么处在「描述该命令本身」的语境（如 README 表格、禁止组合表），不存在「指示 Agent 去跑 `/code-review`」却不带档位的句子。
4. **无禁止组合**：搜 `sonnet` 的每一处出现，确认只与 `medium` 同现（禁止组合表除外）；搜 `opus` 确认只与 `high` 同现（同上除外）；全仓不存在把 `xhigh` 当作可传档位的句子。

补充：人读一遍新 `SKILL.md`，确认从头到尾只有一条 reviewer 路径、且「保留能力清单」六项（迭代环 / 三要素并闸 / TDD 正序 / 2 轮闸口 / 跳过判定 / 留痕）逐条仍在。

## 六、本轮不存在自举风险（一处早期误判的更正）

早期版本假设「目录级软链 ⇒ 改完即刻生效 ⇒ 本轮 commit 会用新规则审自己」。**实测该假设错误**：

```
~/.claude/skills/review-loop -> /Users/wujie/Personal/claude-code-global/skills/review-loop
~/.claude/CLAUDE.md          -> /Users/wujie/Personal/claude-code-global/GLOBAL_AGENTS.md
```

软链指向**主 checkout**，不是本轮的 worktree。故 worktree 内改 `SKILL.md` / `GLOBAL_AGENTS.md` **对当前会话零影响**——本轮 `/commit` 读到的仍是**旧** skill，新规则要等 `/finish` 合回主分支才生效。

后果两条：

1. **没有「改门禁时门禁失效」的自举危险**，也没有活体验证的机会。想验证新委派路径，只能**手动照新 SKILL.md 跑一遍**（本轮就这么做），并把结果写进 SUMMARY。
2. 本轮 commit 走的是旧 `/review-loop`（默认档 = 主会话裸调 `/code-review`）。**这正是要治的病**。故本轮 commit 前**手动按新规则执行**：委派 `model: sonnet` 子 agent 跑 `/code-review medium`，而不是让旧 skill 裸调。

仍需警惕 round 47 踩过的坑：**规则类文档的问题空间近乎无穷**，reviewer 总能再挖一个边缘场景。置信闸（6.1）+ 2 轮硬闸是既有防线。委派 prompt 里的「已定设计前提」摘要至少要列出：两档设计、删 `low` 档、永远委派、禁止组合、2 轮闸口 —— 否则子 agent 必然回头质疑它们。

**若委派路径当场失灵** → 按 Step 5 降级链退回主会话直跑 `/code-review medium`，并把该失败如实写进 SUMMARY 的「局限性」。委派是省钱手段，不是正确性前提。

## 七、执行顺序

1. `skills/review-loop/SKILL.md` 重写（主体，其余三处都是它的摘要，先定主体措辞）
2. `GLOBAL_AGENTS.md` 同步
3. `skills/commit/SKILL.md` 同步
4. `README.md` 同步
5. 跑第五节四条验收 grep
6. `/commit`（自动触发新版 `/review-loop`，默认档 = 委派 sonnet 子 agent + medium）

## 八、回滚

单一 commit、纯文档改动。`git revert` 即可；软链使其立即回到旧规则，无需重装。
