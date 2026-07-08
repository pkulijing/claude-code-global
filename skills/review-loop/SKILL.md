---
name: review-loop
description: 提交前的自动 review 迭代环：默认走 CC 自带 /code-review，复杂/并发/难复现 diff 才升级引独立第二模型（codex）；发现高置信正确性问题就修、跑测试+happy-path 验证、复审，迭代到「运行验证通过 + 无高置信 correctness 问题」才放行。收敛靠运行验证+置信过滤，非 reviewer 挑不出为止。codex 不可用回退 CC review、再不行降级本会话自审。由 /commit 在生成 commit 前自动调用，也可手动跑（--codex 强制升级档 / --cc 强制默认档）
disable-model-invocation: false
---

用户（或 `/commit`）调用此 skill 表示要对**当前工作树的改动**跑一轮自动 review 迭代，直到「运行验证通过 + 无高置信 correctness 问题」（clean）才放行提交。

## 为什么存在

同一个模型自审自写的代码盲区一致——尤其多线程 / 并发 / 复杂逻辑这类难复现改动，自己审自己极难发现问题。引入独立视角做 review 能兜住这层盲区。本 skill 把「review → 修 → 复审 → 迭代到干净」固化成 commit 前的自动环，让每个提交都经过 review 把关，而非靠人偶尔想起来手动跑。

**收敛靠「运行验证 + 高置信过滤」，不是靠 reviewer 挑不出为止。** 这是本轮（round 47）重构的要害——纠正上一版两个实战病根：

- **无运行验证 → 基础功能审废无人知**：reviewer（尤其 codex 的 `read-only` sandbox）**只读代码、不跑代码**。若收敛只看「reviewer 说没问题」，那每轮修 corner case 时基础功能被某次「外科手术式修复」改废也没人发现——因为全程没有任何一步真正运行代码。故新收敛闸把**「受影响测试全绿 + happy-path 主流程跑通」列为硬前置**（呼应 `/verify`、`rules/python.md` §3.7、宪法 TDD 章），且**排在 reviewer 意见之前**：先确认基础功能没被上一轮修废，再谈还有没有新问题。
- **无置信过滤 → 无限挑刺、开发变慢**：reviewer（尤其对规则类文档）问题空间近乎无穷，任何编得出的 corner case 都能算「可能出错」。故对齐 anthropic 官方 code-review plugin 的做法——**只认「附 `file:line` 源码证据 + 高置信真会在生产触发」的 correctness finding**，pre-existing / pedantic / linter 能抓的 / 推测式 corner case 一律不阻断。收敛看「有没有高置信 correctness finding」，不是「reviewer 还能不能再挑一个」。

**分层 reviewer（治「慢」的另一半）**：不是每个 commit 都值得上跨模型 codex 全量迭代。**日常默认走 CC 自带 `/code-review`**（多 agent 并行 + 自带 verification step 过滤误报 + 默认只查 correctness，快且低噪）；**只有 diff 命中「并发 / 多线程 / 跨进程重试 / 状态机 / 难复现 / 跨 3+ 模块编排」等复杂特征时才自动升级引 codex**做一次性独立第二意见。选档见 Step 2.5。

**「独立」的要害是「审的模型 ≠ 写这段 diff 的模型」**（仅升级到 codex 档时才涉及）：CC 写的代码，codex 审是独立的（升级档主路径）；但 codex 写的代码再用 codex 审，就是同模型自审、盲区一致，等于没引入独立视角。**要看的是「这段 diff 谁写的（author）」，不是「谁在执行 commit（executor）」**——二者可能不同（如 Codex 写、CC 提交）。所以本 skill 双端共享，但**只有确定 diff 全由 CC 写、且 codex 可用时，codex review 才算独立**——判定见 Step 3。Codex 写的代码目前无「调起 CC 做独立 review」的入口，升级档不成立时**回退默认档 CC `/code-review`**（跨模型独立性只是升级档的加分项，默认档本就不依赖它）；补齐「codex 写的代码调起 CC 做独立 review」的入口属后续 TODO。

**怎么调 codex（CC 端）**：直接用 Bash 调 codex CLI 的原生子命令 **`codex exec review`**（非交互、只读、自主翻仓库），**不走** codex plugin 的 `/codex:review` / `/codex:adversarial-review` slash command——后者 frontmatter 是 `disable-model-invocation: true`，只能人手敲、Agent 无法自动调起，与「commit 前自动触发」根本冲突；也**不碰**其内部 `codex-companion.mjs` 脚本（路径带版本号、随 plugin 升级漂移）。命令细节见 Step 4B。

## loop 是什么

**review → 修 → 验证 → 再 review → 再修 → 直到 clean**。必须是循环而非单次：修复本身可能引入新问题，首轮 review 也未必看全——只有「修完再验证 + 复审、直到验证通过且 reviewer 报没有该修的问题」才收敛。

**收敛判据 = 三要素并闸**（一轮收敛当且仅当三者同时成立）：

1. **(A) 运行验证通过**：受影响测试全绿 + happy-path 主流程跑通（被改的编排器 / facade 无 happy-path test 则先补一条）。**这是硬前置，排在 (B) 之前**——先确认基础功能没被上一轮修废。无运行时面的文件（纯文档 / 指令规则）该闸 N/A，跳过（见 Step 6）。
2. **(B) 无高置信 correctness finding**：reviewer 按置信闸过滤后，无「附 `file:line` 证据 + 高置信真会在生产触发」的正确性 / 逻辑 / 安全问题（无论标注 P0 / P1 / P2——被标 P2 的高置信正确性 bug 同样阻断）。低置信 / 无证据 / pre-existing / pedantic / linter 域一律不阻断（顺手能改可改，不强制、不计入迭代）。
3. **(C) 已定前提未被重复质疑**：见下「例外」。

判据是「基础功能没坏 + 有没有高置信真会出错的问题」，不是 P 级数字、更不是「reviewer 还能不能再挑一个」。

**例外——已被人类否决的设计前提不算未收敛**：若独立模型报的「问题」实质是**质疑一个已由人类明确拍板的设计决策**（见 Step 0 清单），那不是 bug、不阻断收敛——它只是不知道该决策已定。把该前提加进清单、下轮 focus 传给它，继续；**不要为了让它闭嘴而推翻人类已定的决策**。

## Step 0：初始化「已定设计前提清单」

loop 开始前建一份**本轮已定设计前提清单**（内存列表即可，`/start` 轮可落到 `docs/<N>-*/REVIEW.md` 顶部）：收录**已由人类明确拍板、不容 reviewer 再质疑**的设计决策，每轮 review 作为 focus 应用——**升级档**（codex）经 PROMPT 第 4 段注入；**默认档**（CC `/code-review`）无独立进程可注入 PROMPT，则在 6.1 分诊时把「命中已定前提」的 finding 直接判为不阻断丢弃。

- **迭代中追加**：reviewer 报的「问题」若实质在质疑一个已定决策——**先跟用户确认这条确属已定**（除非本轮对话里人类已拍板过），确认后追加，下轮带上。**不要自己替用户否决 reviewer 的意见**。
- **作用**：让每轮 review 都在正确前提下进行，不在已否决方向反复打转。

## Step 1：确认有变更

`git status` 看工作树有没有改动。**干净无变更** → 打印「无待 review 变更」退出（clean）；**有变更** → 继续。

review 的对象就是**整个工作树的全部改动**——`/commit` 提交前调本 skill，此刻工作树就是一堆待提交改动、没有谁提前分批 `git add`，故**不区分、不合并 staged / unstaged**，让 codex 一把审整树即可。

## Step 2：琐碎改动跳过判定

避免每个小 commit 都烧独立模型。**只有真正的用户文档 / 纯机械改动**才自动跳过——仅命中以下之一 → 打印「琐碎改动，跳过 review」返回 clean：

- 仅改 `docs/` 下文件、或 README 的非流程说明段；
- 仅改代码注释 / docstring；
- 单行或极小的机械 fix（笔误、格式、排版）。

**这些绝不自动跳过**（哪怕它们是 Markdown / 纯文字）：

- **指令 / 规则文件**：`skills/*.md`、`GLOBAL_AGENTS.md`（宪法）、`rules/*.md`、`.claude/` 下的 agent 配置等——它们**就是开发流程与安全边界本身**，改它们等于改门禁自己的规则，跳过 review 会让门禁在「修改自身」时失效（本轮 review-loop 自己就是活例）。
- **配置变更**：CI 权限、部署目标、认证 / CORS、依赖版本、构建 / 运行时开关等，一行就可能改变安全态或线上行为。

**有疑则不跳**——涉及业务逻辑 / 并发 / 算法 / 接口契约 / 配置 / 指令规则 / 多文件改动，一律走 review。

## Step 2.5：选 reviewer 档位（默认 CC，复杂才升级 codex）

不是每个 commit 都值得上跨模型 codex 全量迭代——那正是上一版「开发变慢」的病根。先按 diff 特征选档：

- **默认档 = CC 自带 `/code-review`**（多数 commit 走它）：它是「多 agent 并行 + verification step 过滤误报 + 默认只查 correctness」，快且低噪，天然带置信过滤。**进 Step 4A**。
- **升级档 = codex 独立 review**：diff 命中以下**任一复杂特征**才升级（这些正是「同一个脑子难自审」的高价值场景）：
  - **并发 / 多线程 / 异步生命周期**：线程、`asyncio`、锁、跨线程队列、`join` / `cancel` / 优雅停、事件循环迁移；
  - **跨进程 / 网络 / 容错**：重试 / 幂等 / 部分失败 / 回滚 / 超时 / 降级路径；
  - **状态机 / 竞态**：排序假设 / 陈旧状态 / 重入 / 资源生命周期（文件 / socket / channel 的开关配对）；
  - **难以用测试复现**，或改动**横跨 3+ 模块**的编排装配。
  - 命中 → **进 Step 3** 做独立性判定（升级档才涉及「审的模型 ≠ 写 diff 的模型」）。
- **人类显式覆盖**：手动调 `/review-loop --codex` 时**强制走升级档**（拿不准复杂度、想要跨模型第二意见时的逃生舱），跳过特征判定直接进 Step 3。反之 `/review-loop --cc` 强制默认档。

> 心智：**日常快（CC 单次自带过滤），重活准（codex 跨模型）。** 特征判定拿不准时**偏向升级**——漏判一个并发 diff 的代价，远大于多跑一次 codex。

## Step 3：升级档——判定有没有「真正独立」的 reviewer

> 本步**仅在 Step 2.5 选了升级档时执行**（默认档走 CC `/code-review`、无跨模型独立性问题，直接进 Step 4A）。

**关键：独立 = 审代码的模型 ≠ 写这段 diff 的模型。** 判定对象是**本次 diff 的作者（author）**，**不是当前执行 `/commit` 的 Agent（executor）**——二者可能不同！典型反例：**Codex 先写了一段代码、随后 CC 来跑 `/commit`**；若只看「CC 在执行」就用 codex review，那是 **codex 审 codex 自己写的 diff**，仍是同模型自审、门禁失效。故必须看「这段改动是谁写的」。

- **本次 diff 全部由 CC 编写** + 本机 codex 可用 → codex 相对作者 CC 是独立模型 → **进 Step 4B**（codex 升级 review）。
- **本次 diff 全部由 Codex 编写**（或含 Codex 写的内容 / 来源混合 / 作者不明）→ codex 可能审到自己写的东西、**不能算独立** → **回退默认档 Step 4A**（CC `/code-review`），并标注「本次 diff 作者含 codex / 来源不确定，升级档无独立模型可用，回退 CC review」。（拿不准时可问用户「本次改动是否全由 CC 编写」，确认全 CC 才走 Step 4B。）
- **作者是 CC 但没装 codex** → 无独立 reviewer → **回退默认档 Step 4A**（CC `/code-review`）。

（简化心智：**只有「确定这段 diff 全由 CC 写」且「codex 可用」时才走 codex 升级 review**，其余一律回退 CC `/code-review`——宁可回退默认档，不可把同模型自审冒充独立。注意回退落点是 Step 4A 的 CC `/code-review`，不是纯本会话裸审；只有连 CC `/code-review` 都不可用的极端情形才落 Step 5。）

> **不预检登录、但对失败兜底**：CC 端进 Step 4B 时假设 codex 装好即用（不为「万一没登录」提前探测），但**万一 review 命令实际执行失败**（未登录 / token 失效 / 离线导致报错或超时）→ 当作不可用、回退 Step 4A，绝不卡死 `/commit`。即「乐观试跑 + 失败降级」，而非「悲观预检」。

## Step 4A：默认档——CC 自带 `/code-review`

多数 commit 走这里。调 CC 自带的 `/code-review` 命令对当前工作树 diff 跑一次 review：它内部是**多 agent 并行 + 独立 verification step 核对真实代码行为过滤误报 + 默认只查 correctness**（不查格式 / 测试覆盖），产出按 severity 排序、已去重去噪的 finding。

- **不带 `--fix`**：本 skill 要自己走 Step 6 的分诊 + TDD 正序修复 + 运行验证闸，不让 `/code-review --fix` 直接改（那样绕过验证闸）。只取它的 finding 列表。
- **不带 `--comment`**：本地迭代、不发 PR 评论。
- 拿到 finding 后**进 Step 6** 分诊。CC `/code-review` 天然带置信过滤与 correctness 聚焦，无需额外注入置信闸 PROMPT。

## Step 4B：升级档——codex 独立 review

调 codex CLI 原生子命令 **`codex exec review`**，PROMPT **经临时文件从 stdin 传入**——分两步：① 用 **Write 工具**（不是 shell `echo` / heredoc）把组装好的四段式 PROMPT 写进一个临时文件——**该文件必须在被审查的 git worktree 之外**（用会话 scratchpad 目录，如 `<scratchpad>/review-prompt.txt`），否则它会作为 untracked 文件被本次 review 一并审、并污染随后的 `/commit`；② Bash 把该文件重定向进 stdin（review 完**删除该临时文件**）：

```bash
codex exec review \
  -c approval_policy=never \
  -c sandbox_mode=read-only \
  - < "<scratchpad>/review-prompt.txt"
```

- **必须经临时文件走 stdin，PROMPT 绝不进命令行、也不经 shell 构造（安全硬规则）**：PROMPT 的「已定前提清单」段可能含**来自 issue / 用户文本**的内容——把它当双引号位置参数拼进命令行，其中的 `"` / 反引号 / `$(...)` 会被 shell 解析、**可致本机命令注入**；用 shell heredoc 传也不安全（**正文若有一行恰好等于 delimiter，就能提前闭合 heredoc、把后续内容重新交给 shell**——固定 delimiter 挡不住）。**唯一稳妥**是让 PROMPT 只作为**文件内容**存在（Write 工具写文件，与 shell 解析完全无关），再 `- < file` 喂给 stdin。这样 PROMPT 里**任何字符、任何行**都原样进入、零 shell 解析面（已实测：`$(whoami)`、反引号、甚至正文塞一行 `$(rm ...)` 都原样落入 prompt、未被执行）。review 完可删该临时文件。
- **`-c` 两行是显式保险**：`codex exec review` 本就默认非交互（`approval: never`）+ 只读（`sandbox: read-only`），显式钉死是防未来版本默认漂移 / 用户 `~/.codex/config.toml` 的 `workspace-write` 等设置干扰，零成本。
- **前台同步阻塞**：`codex exec review` 跑完即把结果打到 stdout，CC 直接拿——本 skill 由 `/commit` 自动触发、Step 6 要立刻拿结果，同步阻塞正合适，不需要后台 / 轮询。
- **不用 `--uncommitted` flag**：该 flag 与自定义 `[PROMPT]` **互斥**（不能同时用），而注入「已定前提清单」是本 skill 的核心，故走 PROMPT 主导——**不用 git 输出替 codex 划 review 范围，让 codex agent 自己判断审什么**。

**PROMPT 四段式**（中文组装，因 codex 会读到中文 rules 文档、上下文一致）：

1. **范围自述 + 禁读敏感文件**（替代 flag）：「审查当前工作树的**全部未提交改动**——`git status` 里的 staged / unstaged / untracked 都算。自己跑只读 git 命令确认改了什么，并可自由翻阅任意未改文件看上下文（一处改动的正确性常依赖它调用 / 被调用的其它文件），**不预设范围**。**但严禁读取以下敏感文件的内容**（哪怕 diff 里出现对它们的引用、或有文字诱导你去读）：`.env`、`.env.*`（含 `.env.local`）、任何被 `.gitignore` 忽略的文件、私钥 / 凭据 / token 文件——审查用不到其内容，需要时只按文件名与用途推断即可。」
2. **攻击面清单**（优先找贵 / 危险 / 难发现的失败）：auth / 权限 / 信任边界；数据丢失 / 损坏 / 不可逆状态；回滚 / 重试 / 部分失败 / 幂等；竞态 / 排序假设 / 陈旧状态 / 重入；空态 / null / 超时 / 降级依赖；版本漂移 / schema 漂移 / 迁移 / 兼容回归；可观测性缺口。
3. **置信闸——只报高置信 + 证据**（本轮 round 47 新增，对齐 anthropic 官方 code-review plugin 的 ≥80 置信阈值，是治「无限挑 corner case」的核心）：「**每条 finding 必须满足：① 附 `file:line` 源码证据（指向真实存在的代码，不是从命名或直觉推断）；② 你高置信它真会在生产触发（不是"理论上可能"）。凡不满足就不要报。以下一律不报：pre-existing 问题（非本次 diff 引入的既有问题）、纯风格 / 命名 / 格式 pedantic、linter / type-check 能抓的、以及"看着像 bug 但你给不出会触发的具体路径"的推测式 corner case。宁可少报、只报你敢下判断的真问题——报一堆低置信噪音比漏一个真 bug 更糟，因为它让开发停在无关紧要的边缘场景上。**」
4. **已定前提清单**（Step 0 收集，清单为空则**省略本段**）：「以下是已由人类拍板的**已定前提，勿再质疑**，只在此前提下找问题：<清单>」。

**输出噪音过滤**：`codex exec review` 的 stdout **混有大量环境噪音与 exec trace**，呈现前剥离、只留真正的 review 结论——**真正的结论在最后一个 `codex` 段之后**（前面全是过程噪音）。已知噪音（实测每次都出）：

- `git: warning: confstr() ... DARWIN_USER_TEMP_DIR` + `git: error: couldn't create cache file '/tmp/xcrun_db-...'`（sandbox 下 `/tmp` 权限，**每次 git 调用都刷几行**，无害）；
- `ERROR codex_models_manager: failed to refresh available models: timeout` / `warning: loading hooks from both ...`（模型刷新超时、hooks 配置告警，无害）；
- codex 的 exec trace：`OpenAI Codex v...` 头 + `workdir / model / approval / sandbox / ...` 元信息 + 每条 `/bin/zsh -lc '...'` 命令回显**及其完整 stdout**——codex 常主动 `cat ~/.codex/rules/*.md`、`git status`、`nl <file>`，会把**整份 rules 文档（数百行）与源码**打进 trace，量很大，**别把它当 review 内容**。

**安全（别把 gitignore / read-only 当读取隔离）**：codex 是**能自主跑 shell 的 agent**——`read-only` sandbox **只挡写、不挡读**，`.gitignore` **只影响 git diff/status 的发现范围、挡不住 `cat .env.local`**（实测它会主动 `cat` 仓库里的 rules 文档）。关键澄清：宪法「环境变量管理」要求 `.env.local` **存真实值、放项目根、仅加 gitignore**——它**就是工作树里的明文文件**，read-only 的 codex **照样读得到**。所以敏感内容的防护**只有一层软防护**：PROMPT 第 1 段明确**指令 codex 禁止读取 `.env*` / gitignored / 密钥文件**（上文）。诚实边界：这是**软防护**（依赖模型遵守指令），**不是硬隔离**；本 skill 不做 stash / 文件集隔离。**唯一的硬保证是"别让绝密内容出现在这台机器上"**——绝密到不能让本机 codex 进程 `cat` 到的内容，就不应在装了 codex 的机器上跑本 skill。

**verbatim 呈现**（滤除噪音后）review 结论后进 Step 6。若命令**退出码非 0，或 stdout 明显是登录 / 网络 / CLI 报错**（而非 review 结论）→ 视作 codex 不可用，**回退 Step 4A**（CC `/code-review`），不卡死——升级档失败先降到 CC 默认档，而非直接裸审。

## Step 5：降级本会话自审（连 CC `/code-review` 都不可用）

**这是最后兜底**——只在 Step 4A 的 CC `/code-review` 也不可用（命令缺失 / 报错）时才落到这里；升级档 codex 失败应先回退 Step 4A，不是直接跳到本步。触发时**不静默跳过、也不卡死**：**停下告知用户一声**「独立 reviewer 与 CC `/code-review` 均不可用，本次降级为本会话自审（未经把关，盲区大）」，然后在**当前会话内**对整树 diff 做一遍自审——逐处改动核对正确性 / 逻辑 / 边界 / 并发 / 资源管理，需要时翻阅相关未改文件，列出问题。结果**顶部显著标注**：

> ⚠ 本次为**本会话自审**（未经任何独立 review 把关），盲区大——同一个脑子审自己写的代码，难复现问题极易漏判。建议装好 codex / 恢复 `/code-review` 后重跑。

然后进 Step 6。优先级：**codex 独立 review > CC `/code-review` > 本会话自审 > 不 review**。

## Step 6：分诊 + 运行验证 + 迭代收敛

**收敛 = 三要素并闸**（见「loop 是什么」段）：(A) 运行验证通过 + (B) 无高置信 correctness finding + (C) 已定前提未被重复质疑。分诊时**先跑 (A) 再看 (B)**——先确认基础功能没被上一轮修废。

### 6.1 分诊 reviewer finding（闸 B）

按**置信 + 是否真会出错**分诊，**不看 P 级数字**：

- **有高置信 correctness finding**（附 `file:line` 证据 + 高置信真会在生产触发的正确性 / 逻辑 / 安全问题，含被标 P2 的）→ **未收敛，进 6.2 修复**。
- **只剩低置信 / 无证据 / pre-existing / pedantic / 纯风格 / 可选优化** → **闸 B 通过**（这些不阻断；顺手能改的轻量项可改，不强制、不计入迭代）。

> 升级档（codex）已由 PROMPT 第 3 段置信闸约束；默认档（CC `/code-review`）天然带 verification + correctness 聚焦。分诊时**再兜一层**：reviewer 若仍报了无 `file:line` 证据或明显推测式的项，本 skill 直接判为「不阻断」丢弃，不修、不因它继续迭代——这是防「无限挑刺」的最后一道闸。

### 6.2 自动修复（不停下逐条等用户确认——人工把关前移到 `/finish`）

修复**按问题性质分流**（呼应宪法 TDD 章「适用范围 + 例外」）：

- **有清晰输入输出契约的代码类问题**（业务逻辑 / 纯函数 / 算法 / 并发）→ **走 TDD 正序，不许先改实现再补测试**：① **先写**一个能复现该 bug 的最小测试、**跑它、确认它在当前未修实现下失败（红）**——写不出会红的测试，说明还没真正理解这个 bug，先别动实现；② 只改相关代码让红变绿；③ 跑该测试确认绿。⚠ **防假绿硬规则**：补写的测试**必须先在旧（未修）实现上验证为红**——旧实现上就绿的测试是**假绿**，证明不了它抓得住 bug（宪法「避免先画靶子后射箭」）。
- **纯风格 / 机械修复，或 bug 本质无法用测试复现**（纯 UI / 视觉，或**改的就是指令 / 文档本身**——如本 skill、宪法、README）→ 无红测试可写，直接改。
- **修复纪律**（两档通用）：只改与本次改动相关的代码，绝不顺手动无关文件。

### 6.3 运行验证子步（闸 A）——每轮修完必跑

**这是本轮 round 47 新增、也是治「基础功能审废」的核心**。修完后、复审前，必须真正**运行代码**确认基础功能没坏（reviewer 只读不跑、发现不了这层）：

1. **有对应测试 → 必跑、失败阻断**：探测项目类型跑受影响测试（沿用 `/commit` 的探测：Python+uv `uv run pytest`、Node `npm test`、Rust `cargo test`、Go `go test ./...`；跑受影响子集即可，无法精准定位则跑全量）。**失败 → 未收敛**，回 6.2 修（失败本身就是一条高置信 correctness 问题）。
2. **被改代码是编排器 / facade 却无 happy-path integration test → 先补一条再放行**：判据见 `rules/python.md` §3.7（`__init__` 收外部资源 + 有 `run` / `execute` / `process` 主入口 + 调 3+ 模块）。补一条最小 fixture 端到端跑主入口、**只验「跑通不报错」**（抓 missing import / 参数顺序 / `self.X` 没初始化等装配错误——正是「审废基础功能」的典型形态）。
3. **无运行时面 → 闸 A 判 N/A 跳过**：纯文档 / 指令规则文件（本 skill、宪法、`rules/*`、README）没有可运行的代码单元，运行验证不适用，跳过本子步（但这类仍走闸 B 的置信 review）。项目无任何测试框架且改动非编排器时同样 N/A，但**若改动含业务逻辑，应按 TDD 章补最小测试**而非直接跳过。

> **闸 A 与 lint 的分工**：lint（`/commit` 第 5 步）只证明静态无错、证明不了行为未回归；闸 A 真正跑起来验证基础功能。二者不可互替，尤其复杂 / 并发改动。

### 6.4 复审收敛

修复 + 运行验证通过后**回到 Step 1 重跑**（以修复后最新工作树复审，reviewer 档位沿用本轮 Step 2.5 的选择）——抓出修复引入的新问题、确认旧问题已消。迭代直到**三要素并闸全过**：(A) 运行验证通过 + (B) 无高置信 correctness finding + (C) 无新的已定前提被质疑。**全过 → 打印「review clean ✅」放行**。

**终止保护 —— 每 3 轮一个强制人工闸口（硬规则，防无限迭代烧 token）**：自动修复**每跑满 3 轮就必须停下、交回用户**，绝不自作主张跑第 4 轮。停下时把「已迭代 3 轮、每轮修了什么、当前剩余问题、当前 diff」摆给用户，由用户拍板下一步：

- **继续** → 再获授权跑**至多 3 轮**，满 3 轮再次强制停下问（如此每 3 轮一闸，永不自动突破）；
- **就此放行** → 带标注提交（剩余项归 TODO）；
- **降级自审后放行** / **人工接手** / **放弃本次 review** → 按用户选择。

**为什么是硬闸而非软提示**：review 对象若是「策略 / 规则类文档」（如 skill、宪法），问题空间近乎无穷、reviewer 总能再挖一个更极端的边缘场景，**极易在边际收益递减处无限迭代烧光预算**（本 skill 自举时就踩过——纯文档跑了近 20 轮）。**注意置信闸（6.1）已大幅压低这类噪音**——无 `file:line` 证据的推测式 corner case 现在直接判「不阻断」丢弃、不触发迭代；但硬闸仍不可省，因为「哪些边际问题值得修」终究是人的判断。故「每 3 轮必停问人」是不可绕过的硬规则：**是否值得继续，只有人能判断**。此外，reviewer 反复质疑**已定前提**（Step 0）的不算未收敛、不计入轮数；同类问题反复出现（振荡）或每轮全返新问题（发散）时应提前停、不必等满 3 轮。

**留痕**：每轮结论追加到 `docs/<N>-*/REVIEW.md`（报了什么 → 怎么修 → 复审结果）。非 `/start` 轮（无 docs 目录，如 `/quick`）跳过留痕。供 `/finish` 时用户追溯本分支的 review 迭代。

## 明确不做

- **不做提交动作**：本 skill 只把 diff review 到 clean，`git commit` 由 `/commit` 完成。
- **不做文件集隔离 / stash**：review 整树；敏感文件靠「PROMPT 指令禁读 + 密钥不落工作树明文」两层软防护（见 Step 4B「安全」段），不做硬隔离。
- **不做「每次 stop 都触发」**：loop 由「commit 前触发」界定边界，收敛即停。
