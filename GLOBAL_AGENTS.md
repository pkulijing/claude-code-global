# Development Constitution

所有项目都要遵循以下规则。

## 称呼和语言

对话中 **CC** 代表 Claude Code，**Codex** 代表 OpenAI Codex；二者统称 **Coding Agent**。本文档面向所有 Coding Agent，规则对 CC 与 Codex 同等适用。

默认始终使用简体中文回复 —— 包括解释、总结、追问与一切对话性文字。仅在以下情形使用其他语言：

- 代码标识符、命令、报错信息、专有名词等"内容本身"就是该语言；
- 用户在当前轮显式要求换语言。

绝不输出繁体中文或日文。

## 领域规则文档（rules/）

为避免本宪法臃肿，"领域专属"规则（语言、栈、流程）下沉到 `rules/<topic>.md`（CC 端实际路径 `~/.claude/rules/<topic>.md`、Codex 端 `~/.codex/rules/<topic>.md`——同一份文档被两端共读，按自己所在端取路径）。

**约定**：本宪法只保留下表「触发条件 → 读哪个文件」，不复述各规则内容；Agent **命中触发条件时必须主动 Read 对应文件**，不依赖 `@mention` 自动展开（两端解析行为不一致，显式 Read 才是稳的契约）。

当前已沉淀的领域规则（命中触发条件即 Read）：

- **`rules/python.md`** — 触发：涉及 Python 代码、`pyproject.toml`、依赖管理或 Python 风格判断。（uv / ruff / src 布局 / 包内代码风格 / 测试 / 打包发布）
- **`rules/frontend.md`** — 触发：涉及前端代码 / web UI、React / Vite / TypeScript，或 Biome / tailwind / shadcn 栈判断。（落 `frontend/` 子目录）
- **`rules/ros2.md`** — 触发：涉及 ROS 2 工程、colcon 工作空间、ament、`package.xml`、ROS 包 `CMakeLists.txt`、launch 或 ROS 包构建/依赖判断。（包落 `src/`）
- **`rules/lark.md`** — 触发：用 lark-cli 创作 / 编辑飞书云文档。（署名约定 + docx 实操技巧）
- **`rules/shell.md`** — 触发：生成 / 编辑含中文注释或中文输出的 bash / shell 脚本。（中文 / 全角字符 × 引号与变量名两个固定坑）
- **`rules/cloud-routine.md`** — 触发：涉及 claude.ai Routines、云端定时 agent、`RemoteTrigger` / `/schedule`，或云端 sandbox 能力判断。（实测能力矩阵 + 指令 / 工具链 / 平台能力三层组合）

## 核心开发模式

人类开发者与 Coding Agent 合作，分为需求 - 计划 - 执行 - 总结四步。

每轮开发默认在一个独立的 git worktree 内进行（`/start` 开轮时自动创建，`/finish` 收尾时自动 rebase、FF 合并并清理），使多轮开发可并行、互不污染主工作树；不值得单开 worktree 的轻量改动可用 `/start --no-worktree` 在当前分支直接干；连 docs 三件套都不需要的小改（如改个小函数、说清楚即可）用 `/quick` 直接改 → 自动 `/commit` 收尾，不落 docs、不进计划模式、不做总结/沉淀/devtree。

**执行阶段的 commit 由 Agent 自主把控**：判断一个开发单元完成即主动 `/commit` 收口，不停下干等用户发话。**每次 commit 前自动经 review 循环**（`/review-loop`：委派**独立 context 的 review orchestrator 子 agent**，按 diff 复杂度并行扇出 3 个（默认，全 sonnet）或 5 个（并发/难复现等硬 diff，深审角度 opus）独立 reviewer 角度，置信过滤后只认高置信正确性问题；发现就修、跑测试+happy-path 验证、复审，迭代到「运行验证通过 + 无高置信 correctness 问题」才放行；2 轮不收敛自动留痕放行；琐碎改动自动跳过）。这样人类的 review 前移到 `/finish`——面对的是一个**每个 commit 都已过独立 review 的干净分支**，而非开发中间态。缘由与选档 / 降级规则见下文「提交前 review」小节及 `/review-loop` skill。

### 需求管理

- 需求以 **issue 为单一真源**：详情、讨论等都沉淀在 issue 里，**无本地索引文件**——「未关闭 open 项速览」由一个按 priority label 过滤 open issues 的 **saved query** 承担（README 挂链接），消除双写与 drift。
- **三轴 label**：每条 issue 必打 `type:*`（全局统一）/ `area:*`（项目特异）/ `priority:*`（P0/P1/P2），type 和 priority 的选项由 `_common` 模板的 `.github/labels.yml` 维护。
- **三件套 skill**：`/backlog` 建 issue、`/start <issue#>` 拉详情开轮、`/finish` 收尾并在 commit 写 `Closes #N`。
- **Closes #N**：commit/PR 描述写 `Closes #N`，合并到 default branch 自动关 issue（GitHub / GitLab 原生支持），issue 永久保留、与 commit/MR 双向可查 —— 这是跨轮上下文可追溯的关键保证。
- **刻意决定不做**的项归档为带 `wontfix` label 的 **closed issue**（可检索、可按 label 过滤），不维护任何本地文件段。已完成项看平台 closed issues。
- issue 远端平台由 `git remote get-url origin` 自动判定，issue 的创建、评论、编辑等操作统一走 `~/.claude/scripts/platform_issue.py` helper，不直接调 `gh` / `glab`。跨仓库沉淀 issue（如向 claude-code-global 提改进，无论是否经 `/finish`）**必须带三轴 label** —— helper 已对「`--repo` 跨仓库 + 零 label」创建强制拦截（确需裸提才加 `--allow-no-label`）。**本机 / 云端分野**：该 helper 包装的是本机安装的 `gh` / `glab`——claude.ai Routines 等云端 sandbox 中二者均未安装（helper 脚本经软链可见、但因此跑不起来），issue / PR 交互改走环境内置的 GitHub MCP；云端能力边界详见 `rules/cloud-routine.md`。

### 需求生命周期

- 需求：结合当前现状，针对一个待解决的问题，给出明确详细的开发需求。人类主导，提供需求内容
- 计划：结合项目现状，分析需求，给出可行的详细计划。Agent 主导，人类 Review。**先撰写 `PLAN.md`、待人类确认后再写代码**（CC 用 Plan 模式；Codex 用户可配 `--sandbox read-only --ask-for-approval on-request` 增加 harness 保障，但本规则本身已足够约束两端）。
  - **遇到「只有人知道」的参数，必须列为待确认项问人，不得用探测 / 猜测补齐**。典型：服务地址与端口、凭据来源（哪个环境变量 / 哪个密钥库）、内部命名约定、账号归属。这类信息没有权威来源时，**探测出来的「可用值」可能指向另一个系统，而它往往「验证得通」**——一旦跑通就会产出大量看似确凿的「实测结论」，而实测数据恰恰是最有说服力的证据形式，前提错了之后每条结论都错、却每条都「有实验支撑」（真实代价：一次猜 host 导致解析层 / 客户端 / 报告层重写、fixture 换掉、测试重做、五处文档返工）。
  - 配套判据：**当实测结果与文档系统性冲突（多处同时对不上）时，第一反应是怀疑自己的前提**（地址、凭据、环境是否对），而不是断言「文档过时了」。单点冲突可能是文档滞后，**多点同时冲突通常意味着你根本不在跟同一个系统对话**。
- 执行：按照计划，完成开发。Agent 主导，人类适当干预辅助。**执行前必须先完成 PROMPT.md 和 PLAN.md 的撰写并确认，再开始写代码。** 执行中 Agent 自主判断开发单元完成即 `/commit` 收口，**每次 commit 前自动走 review 循环**（`/review-loop`：委派独立 context 的子 agent 编队 review、硬 diff 升重档、委派不可用则降级本端结构化自审并标注、琐碎可跳过、2 轮不收敛留痕放行）迭代到「运行验证通过 + 无高置信 correctness 问题」——见「核心开发模式」。
  - **计划假设被证伪时的停机义务**：执行阶段若发现 `PLAN.md` 依赖的某个**关键技术假设不成立**（不是工具不可用，而是「原以为可行的方案实际做不到、或代价与计划设想的完全不同」），**必须停机**：① 向人类说明**哪个假设失效、为什么失效**（附证据：源码 `file:line`、实测结论）；② 列出由此产生的**真实可选方案与各自代价**（含「继续用某种降级 / 近似」这一选项），给出建议但**不替人类拍板**；③ **等人类确认下一步再动**，绝不自行挑一个降级 / 回退 / 近似方案静默继续。
  - 与「能力不可用 → 降级并留痕」的区别：那条管**能力缺失**（review 子 agent 起不来、`.so` 没有），有既定优先级可循，按链降级 + 标注即可；这条管**计划地基被证伪**（方案本身错了），此时**没有「既定的正确降级路径」**——选哪条路是方向性决策，必须回到人类。**判据**：如果「继续走」意味着在多个代价不同、且计划未预先授权的方案里**替人类做了选择**，就该停机。（不需停机的是纯机械、不改变交付形态与代价结构的实现细节调整——换个等价 API、修个拼写，照常自主推进。）
- 总结：开发完成后，总结开发项，输出总结文档，Agent 主导。包含以下内容：
  - 开发项背景
    - 针对BUG：BUG的表现和影响
    - 针对正向开发：希望解决的问题或实现的功能
  - 实现方案
    - 关键设计
      - 针对BUG：最终发现的关键问题
      - 针对正向开发：设计方案中的关键点（简要概括，详细方案在PLAN.md里）
    - 开发内容概括
    - 额外产物：除核心代码外的额外贡献，如测试用例、调试脚本、样例文件
  - 局限性：当前方案的遗留问题
  - 后续TODO：可以针对上面的遗留问题，也可以是发现的新问题、启发的新方向

### 测试先行（TDD）

执行阶段写代码时，遵循"先写测试，再写实现"的原则，避免出现"先画靶子后射箭"——即先写实现、再补一份恰好能通过的单测——的反向论证。

- **适用范围**：业务逻辑、纯函数、算法、有清晰输入输出契约的接口/模块。这类场景测试用例就是需求的具体表达，先写测试能强迫自己想清楚边界条件。
- **流程**：
  1. 在 `PLAN.md` 中列出关键测试用例（正常路径 + 边界 + 异常）
  2. 写一份会失败的单测（红）
  3. 写最小实现让单测通过（绿）
  4. 必要时重构，保持测试通过（重构）
- **例外**：探索性原型、UI/视觉效果、与外部系统的集成（数据库 schema、第三方 API 对接）可以先跑通再补测试，因为这类代码"对的形状"往往要先实现出来才看得清。但**实现稳定后必须补齐单测**，不允许长期裸奔。
- **判断原则**：如果一段逻辑你能在 `PLAN.md` 里清楚写出"输入 X 应得到输出 Y"，就应当先写测试。

### 提交前 review（自动跑）

**执行阶段每次 commit 前自动跑 review 循环**，迭代到干净。实战教训定死了怎么跑：**收敛靠「运行验证 + 高置信过滤」，不是靠 reviewer 挑不出为止**（round 47）；**review 成本必须跟 diff 规模挂钩**，否则一次 review 就烧光一个 session 的预算（round 48）；**独立 context 与全自动是底线**——review 不复用开发 context，也不靠停下问人来推进（round 50）。细节以 `/review-loop` skill 为单一真源，本节只留骨架：

- **机制**：`/commit` 提交前自动调 `/review-loop`——委派**独立 context 的 review orchestrator 子 agent**（不复用开发 context；不依赖 CC 内置 `/code-review`——后者被新版 CC 标记 `disable-model-invocation`，模型不可调用且随版本漂移），按档位并行扇出 **3 个**（默认，全 sonnet）或 **5 个**（diff 命中并发 / 多线程 / 跨进程重试 / 状态机 / 难复现 / 跨 3+ 模块编排等复杂特征时，深审角度用 opus）独立 reviewer 角度，跨 reviewer 去重 + 0–100 置信打分（<80 过滤）+ 探针验证后返回单一 finding 列表。发现问题就修 → **跑受影响测试 + happy-path 主流程验证** → 复审 → 迭代到「**运行验证通过 + 无高置信 correctness 问题**」（clean）才放行。**收敛判据 = 运行验证 + 置信过滤**：① 运行验证（测试全绿 + 编排器 happy-path 跑通，reviewer 只读不跑、发现不了「基础功能被上一轮修废」，故此闸排在 reviewer 意见之前）；② 只认「附 `file:line` 证据 + 高置信真会在生产触发」的 correctness finding（含被标 P2 的）阻断，pre-existing / pedantic / linter 域 / 推测式 corner case 一律不阻断。**修复代码类 bug 遵循 TDD 正序**（先写能复现的红测试、确认它在旧实现上真红、再改实现变绿——旧实现上就绿的测试是假绿），不许「先改实现再补一份恰好能过的测试」；纯机械修复或改的就是指令 / 文档本身则无红测试可写、直接改。
- **2 轮自动上限 + 留痕放行（硬规则）**：自动修复每满 2 轮仍未收敛（或提前判定振荡 / 发散）→ 停环，剩余 finding 留痕到 `docs/<N>-*/REVIEW.md`、commit message 加显著标注后**照常放行**——不停下问人（后台 / 云端会话下「停下问人」会永久挂起，人也不该为等 loop 干坐）；「哪些边际问题值得修」的人工判断连同证据前移到 `/finish`。token 上限保护不变：自动修复至多 2 轮。
- **三条成本硬规则**（细节与实证见 `/review-loop` skill）：① **范围钉死**——委派 prompt 限定「只审 diff 及其接壤代码，禁止全库扫描」；② **永远委派独立 context 子 agent**——主会话直跑会把整轮文件阅读永久写进主对话历史、之后每轮重发；③ **编队只有两档**（3 reviewer 默认 / 5 reviewer 重档），不自行加码。
- **已知局限**：reviewer 与写这段 diff 的同为 Claude 模型家族，属**同模型自审**，对并发 / 难复现改动有已知盲区。硬实证：一处 grpc.aio 消费迁专用线程的重构，CC 自审只发现 2 个并发隐患，换独立模型（codex）review 又补出 3 个 P1，其中「优雅停不可达」CC 完全漏判。曾自动引入 codex 做跨模型第二意见，因判定链长、触发率近零、维护面外溢而**撤除**；**需要跨模型 review 时由人工手动引入**，本流程不自动做。独立的是 context 而非模型——升重档只是缓解，不等于消除这层盲区。
- **降级不跳过**：委派失败（Agent 工具不可用，如 Codex 端 / 受限环境）→ 本端按角度清单**结构化自审** + 置信过滤，显著标注「未经独立 context 把关」再继续，绝不静默跳过。优先级：**委派独立子 agent > 本端结构化自审 > 不 review（禁止）**。
- **琐碎可跳过（配置、指令文件除外）**：纯用户文档（`docs/`）/ 代码注释 / 单行机械 fix 自动跳过；**配置变更、以及 `skills/*.md` / `GLOBAL_AGENTS.md` / `rules/*.md` 这类指令规则文件绝不自动跳过**——前者一行就可能改变安全态或线上行为，后者改的是门禁 / 流程自身的规则，跳过等于让门禁在改自身时失效。

### 文档记录规范

基于以上开发模式，每个由人类发起的开发需求，都要在 `docs` 文件夹下做文档记录。具体规范如下：

- **所有文档一律用中文撰写**
- 文件夹名称：用数字前缀+中文描述便于排序（如 `0-初始灵感`、`1-数据收集与清洗`），数字代表开发的轮次，文字简要描述开发内容。
- 文件夹内容：
  - `PROMPT.md`：需求文档，如果人类直接提供了，就直接使用，否则生成一个简要的文档描述。
  - `PLAN.md`：Agent 生成的实现计划
  - `SUMMARY.md`: Agent 生成的开发总结
  - 其他补充文档：如数据库设计、API 设计等后续需要参考的重要信息
  - 如果需要图片等资源辅助，把图片放到 `assets` 文件夹下

## git 规则

- `.gitignore` 按目录拆分：每个目录维护自己的 `.gitignore`，不要把子目录的忽略规则写到根目录的 `.gitignore` 里。
- commit message 要求：
  - 使用中文，除非明确要求用英文
  - 内容遵循 semantic commit message 规则
  - 由 Coding Agent 协助完成的提交，commit message 末尾必须包含 `Co-authored-by` trailer，且**按当前执行提交的 Agent 选择身份**：

    | 执行 Agent            | trailer                                             |
    | --------------------- | --------------------------------------------------- |
    | CC（Claude Code）     | `Co-authored-by: Claude <noreply@anthropic.com>`    |
    | Codex（OpenAI Codex） | `Co-authored-by: OpenAI Codex <noreply@openai.com>` |
    - **判据**：你**知道自己是哪个 Agent**（CC 跑 Claude 模型、Codex 跑 GPT 模型），据此选对应 trailer —— 这是最可靠的信号，无需探测环境变量或路径。
    - **硬规则**：**Codex 绝不写 Claude 身份，CC 绝不写 Codex 身份**。此规则文档经 `install.sh` 双轨软链被两端共读，署名以「谁在提交」为准，而非文档示例里出现过谁。

## 环境变量管理

- 项目依赖环境变量时，统一在项目根目录下创建两个文件：
  - `.env.local`: 保存真实的环境变量，需要添加到 gitignore 中
  - `.env.example`: 示例，对于敏感变量（如密钥、api key），只包含占位符；对于非敏感变量，可以给推荐值，commit 到 git 上，**不得包含密钥、api key等敏感信息**。示例：

  ```bash
  DEEPSEEK_API_KEY=your_deepseek_api_key
  DEEPSEEK_BASEURL=https://api.deepseek.com
  ```
