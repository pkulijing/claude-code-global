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

## 核心开发模式

人类开发者与 Coding Agent 合作，分为需求 - 计划 - 执行 - 总结四步。

每轮开发默认在一个独立的 git worktree 内进行（`/start` 开轮时自动创建，`/finish` 收尾时自动 rebase、FF 合并并清理），使多轮开发可并行、互不污染主工作树；不值得单开 worktree 的轻量改动可用 `/start --no-worktree` 在当前分支直接干；连 docs 三件套都不需要的小改（如改个小函数、说清楚即可）用 `/quick` 直接改 → 自动 `/commit` 收尾，不落 docs、不进计划模式、不做总结/沉淀/devtree。

**执行阶段的 commit 由 Agent 自主把控**：判断一个开发单元完成即主动 `/commit` 收口，不停下干等用户发话。**每次 commit 前自动经 review 循环**（`/review-loop`：默认走 CC `/code-review`、复杂/并发/难复现 diff 才升级引 codex；发现高置信正确性问题就修、跑测试+happy-path 验证、复审，迭代到「运行验证通过 + 无高置信 correctness 问题」才放行；琐碎改动自动跳过）。这样人类的 review 前移到 `/finish`——面对的是一个**每个 commit 都已过 review 的干净分支**，而非开发中间态。缘由与分层 / 降级规则见下文「独立模型 review」小节及 `/review-loop` skill。

### 需求管理

- 需求以 **issue 为单一真源**：详情、讨论等都沉淀在 issue 里，**无本地索引文件**——「未关闭 open 项速览」由一个按 priority label 过滤 open issues 的 **saved query** 承担（README 挂链接），消除双写与 drift。
- **三轴 label**：每条 issue 必打 `type:*`（全局统一）/ `area:*`（项目特异）/ `priority:*`（P0/P1/P2），type 和 priority 的选项由 `_common` 模板的 `.github/labels.yml` 维护。
- **三件套 skill**：`/backlog` 建 issue、`/start <issue#>` 拉详情开轮、`/finish` 收尾并在 commit 写 `Closes #N`。
- **Closes #N**：commit/PR 描述写 `Closes #N`，合并到 default branch 自动关 issue（GitHub / GitLab 原生支持），issue 永久保留、与 commit/MR 双向可查 —— 这是跨轮上下文可追溯的关键保证。
- **刻意决定不做**的项归档为带 `wontfix` label 的 **closed issue**（可检索、可按 label 过滤），不维护任何本地文件段。已完成项看平台 closed issues。
- issue 远端平台由 `git remote get-url origin` 自动判定，issue 的创建、评论、编辑等操作统一走 `~/.claude/scripts/platform_issue.py` helper，不直接调 `gh` / `glab`。跨仓库沉淀 issue（如向 claude-code-global 提改进，无论是否经 `/finish`）**必须带三轴 label** —— helper 已对「`--repo` 跨仓库 + 零 label」创建强制拦截（确需裸提才加 `--allow-no-label`）。

### 需求生命周期

- 需求：结合当前现状，针对一个待解决的问题，给出明确详细的开发需求。人类主导，提供需求内容
- 计划：结合项目现状，分析需求，给出可行的详细计划。Agent 主导，人类 Review。**先撰写 `PLAN.md`、待人类确认后再写代码**（CC 用 Plan 模式；Codex 用户可配 `--sandbox read-only --ask-for-approval on-request` 增加 harness 保障，但本规则本身已足够约束两端）。
- 执行：按照计划，完成开发。Agent 主导，人类适当干预辅助。**执行前必须先完成 PROMPT.md 和 PLAN.md 的撰写并确认，再开始写代码。** 执行中 Agent 自主判断开发单元完成即 `/commit` 收口，**每次 commit 前自动走 review 循环**（`/review-loop`：默认 CC `/code-review`、复杂改动升级 codex、再不可用降级本端自审并标注、琐碎可跳过）迭代到「运行验证通过 + 无高置信 correctness 问题」——见「核心开发模式」。
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

### 独立模型 review（commit 前自动跑）

**同一个模型自审自写的代码，盲区一致、极难发现问题**——尤其多线程 / 并发 / 复杂逻辑这类难复现改动。硬实证：一处 grpc.aio 消费迁专用线程的重构，CC 自审只发现 2 个并发隐患，换独立模型（codex）review 又补出 3 个 P1，其中「优雅停不可达」CC 完全漏判。`/code-review`（自审自己 diff）单独解决不了，因为是同一个脑子。

因此**执行阶段每次 commit 前自动跑 review 循环**，迭代到干净。但两条实战教训（round 47）定死了怎么跑：**收敛靠「运行验证 + 高置信过滤」，不是靠 reviewer 挑不出为止**；且**不是每个 commit 都值得上跨模型 codex**——否则 review 又慢又在犄角旮旯挑刺，甚至把基础功能审废还没人发现。

- **机制**：`/commit` 提交前自动调 `/review-loop`——**默认走 CC 自带 `/code-review`**（多 agent 并行 + verification step 过滤误报，快且低噪）；**只有 diff 命中并发 / 多线程 / 跨进程重试 / 状态机 / 难复现 / 跨 3+ 模块编排等复杂特征时才升级引 codex** 做独立第二意见。发现问题就修 → **跑受影响测试 + happy-path 主流程验证** → 复审 → 迭代到「**运行验证通过 + 无高置信 correctness 问题**」（clean）才放行。**收敛判据 = 运行验证 + 置信过滤**：① 运行验证（测试全绿 + 编排器 happy-path 跑通，reviewer 只读不跑、发现不了「基础功能被上一轮修废」，故此闸排在 reviewer 意见之前）；② 只认「附 `file:line` 证据 + 高置信真会在生产触发」的 correctness finding（含被标 P2 的）阻断，pre-existing / pedantic / linter 域 / 推测式 corner case 一律不阻断。**修复代码类 bug 遵循 TDD 正序**（先写能复现的红测试、确认它在旧实现上真红、再改实现变绿——旧实现上就绿的测试是假绿），不许「先改实现再补一份恰好能过的测试」；纯机械修复或改的就是指令 / 文档本身则无红测试可写、直接改。
- **每 3 轮强制人工闸口（硬规则）**：自动修复每满 3 轮必须停下交回用户、绝不自动跑第 4 轮；用户授权后再来至多 3 轮，如此每 3 轮一闸、永不自动突破。尤其 review「策略 / 规则类文档」（skill、宪法）时问题空间近乎无穷、易无限烧 token——**是否值得继续只有人能判断**。
- **「独立」= 审的模型 ≠ 写这段 diff 的模型**（**仅升级到 codex 档时才涉及**；默认 CC `/code-review` 档不做跨模型独立性判定）：看 diff 的**作者**，不是**执行 commit 的 Agent**——二者可能不同，如 Codex 写、CC 提交。只有**确定 diff 全由 CC 编写**时 codex 审才算独立（CC 端直接调 codex CLI 原生子命令 `codex exec review`，**不走** `disable-model-invocation` 的 `/codex:*` slash command——那种只能人手敲、Agent 无法自动调起；细节见 `/review-loop` skill）；diff 含 codex 写的内容 / 来源不明时，codex 审就是同模型自审、**不算独立**，回退默认档 CC `/code-review`、不得用 codex 冒充独立 review。补齐「codex 写的代码调起 CC 做独立 review」的入口属后续 TODO。
- **降级不跳过**：升级档 codex 不可用时**回退默认档 CC `/code-review`**；连 CC `/code-review` 都不可用才**停下告知用户「本次降级为本会话自审、未经把关」**再继续，绝不静默跳过。优先级：**codex 独立 review > CC `/code-review` > 本会话自审 > 不 review**。
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
