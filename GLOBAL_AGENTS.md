# Development Constitution

所有项目都要遵循以下规则。

## 称呼和语言

对话中 **CC** 代表 Claude Code，**Codex** 代表 OpenAI Codex；二者统称 **Coding Agent**。本文档面向所有 Coding Agent，规则对 CC 与 Codex 同等适用。

默认始终使用简体中文回复 —— 包括解释、总结、追问与一切对话性文字。仅在以下情形使用其他语言：

- 代码标识符、命令、报错信息、专有名词等"内容本身"就是该语言；
- 用户在当前轮显式要求换语言。

绝不输出繁体中文或日文。

## 领域规则文档（rules/）

为避免本宪法臃肿，"领域专属"规则（语言、栈、流程）下沉到 `rules/<topic>.md`：

- CC 端实际路径：`~/.claude/rules/<topic>.md`
- Codex 端实际路径：`~/.codex/rules/<topic>.md`

**约定**：本宪法相应章节只保留"指针 + 触发条件"两句话；Agent 命中触发条件时**必须主动 Read 对应文件**，不依赖 `@mention` 自动展开（两端解析行为不一致，显式 Read 才是稳的契约）。

当前已沉淀的领域规则：

- `rules/python.md` — Python 项目（pyproject.toml / uv / ruff / 包内代码风格 / 测试）
- `rules/frontend.md` — 前端项目（npm / npmmirror / Biome / Vite / tailwind v4 / shadcn / React，落 `frontend/` 子目录）
- `rules/ros2.md` — ROS 2 工程（colcon 工作空间 / ament_cmake + ament_python / package.xml / CMakeLists ament-first 约定，包落 `src/`）
- `rules/lark.md` — lark-cli 创作飞书云文档（署名约定 + docx 实操技巧）

## 核心开发模式

人类开发者与 Coding Agent 合作，分为需求 - 计划 - 执行 - 总结四步。

每轮开发默认在一个独立的 git worktree 内进行（`/start` 开轮时自动创建，`/finish` 收尾时自动 rebase、FF 合并并清理），使多轮开发可并行、互不污染主工作树；轻量改动可用 `/start --no-worktree` 在当前分支直接干。

### 需求管理

- 需求以 **issue 为真源**：详情、讨论等都沉淀在 issue 里
- `docs/BACKLOG.md` 是**未关闭 issue 的扁平索引**
- **三轴 label**：每条 issue 必打 `type:*`（全局统一）/ `area:*`（项目特异）/ `priority:*`（P0/P1/P2），type 和 priority 的选项由 `_common` 模板的 `.github/labels.yml` 维护。
- **三件套 skill**：`/backlog` 建 issue + 写 BACKLOG 索引、`/start <issue#>` 拉详情开轮、`/finish` 收尾并在 commit 写 `Closes #N`。
- **Closes #N**：commit/PR 描述写 `Closes #N`，合并到 default branch 自动关 issue（GitHub / GitLab 原生支持），issue 永久保留、与 commit/MR 双向可查 —— 这是跨轮上下文可追溯的关键保证。
- **已完成项**不在 BACKLOG.md 追踪（看平台 closed issues）；BACKLOG.md 末尾「## 已完成 / 不再追踪」段只记**刻意决定不做**的项 + 原因。
- issue 远端平台由 `git remote get-url origin` 自动判定，issue 的创建、评论、编辑等操作统一走 `~/.claude/scripts/platform_issue.py` helper，不直接调 `gh` / `glab`。跨仓库沉淀 issue（如向 claude-code-global 提改进，无论是否经 `/finish`）**必须带三轴 label** —— helper 已对「`--repo` 跨仓库 + 零 label」创建强制拦截（确需裸提才加 `--allow-no-label`）。

### 需求生命周期

- 需求：结合当前现状，针对一个待解决的问题，给出明确详细的开发需求。人类主导，提供需求内容
- 计划：结合项目现状，分析需求，给出可行的详细计划。Agent 主导，人类 Review。**先撰写 `PLAN.md`、待人类确认后再写代码**（CC 用 Plan 模式；Codex 用户可配 `--sandbox read-only --ask-for-approval on-request` 增加 harness 保障，但本规则本身已足够约束两端）。
- 执行：按照计划，完成开发。Agent 主导，人类适当干预辅助。**执行前必须先完成 PROMPT.md 和 PLAN.md 的撰写并确认，再开始写代码。**
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
  - 由 AI 协助完成的提交，commit message 末尾必须包含 `Co-authored-by` trailer，例如：

  ```
  Co-authored-by: Claude Sonnet <noreply@anthropic.com>
  ```

## 环境变量管理

- 项目依赖环境变量时，统一在项目根目录下创建两个文件：
  - `.env.local`: 保存真实的环境变量，需要添加到 gitignore 中
  - `.env.example`: 示例，对于敏感变量（如密钥、api key），只包含占位符；对于非敏感变量，可以给推荐值，commit 到 git 上，**不得包含密钥、api key等敏感信息**。示例：

  ```bash
  DEEPSEEK_API_KEY=your_deepseek_api_key
  DEEPSEEK_BASEURL=https://api.deepseek.com
  ```

## Python 开发规则

Python 项目（`pyproject.toml` / uv / ruff / 包内代码 / 测试）相关规范集中维护在领域规则文档 **`rules/python.md`**：

- CC 端：`~/.claude/rules/python.md`
- Codex 端：`~/.codex/rules/python.md`

**触发条件**：本轮任务一旦涉及 Python 代码、`pyproject.toml`、依赖管理或 Python 风格判断，**必须先把 `rules/python.md` 读入上下文**，再开始动手。

## 前端开发规则

前端工程（npm / npmmirror、Biome、Vite、TypeScript、tailwind v4、shadcn-ui、React，落 `frontend/` 子目录）相关规范集中维护在领域规则文档 **`rules/frontend.md`**：

- CC 端：`~/.claude/rules/frontend.md`
- Codex 端：`~/.codex/rules/frontend.md`

**触发条件**：本轮任务一旦涉及前端代码 / web UI、React / Vite / TypeScript 前端工程，或 Biome / tailwind / shadcn 等前端栈判断，**必须先把 `rules/frontend.md` 读入上下文**，再开始动手。

## ROS 2 开发规则

ROS 2 工程（colcon 工作空间、ament_cmake + ament_python、package.xml、CMakeLists ament-first 约定、launch、依赖消费/导出、新增包检查清单，包落 `src/`）相关规范集中维护在领域规则文档 **`rules/ros2.md`**：

- CC 端：`~/.claude/rules/ros2.md`
- Codex 端：`~/.codex/rules/ros2.md`

**触发条件**：本轮任务一旦涉及 ROS 2 工程、colcon 工作空间、ament（`ament_cmake` / `ament_python`）、`package.xml`、ROS 包的 `CMakeLists.txt`、launch 文件或 ROS 包构建/依赖判断，**必须先把 `rules/ros2.md` 读入上下文**，再开始动手。

## lark-cli 文档创作规则

用 lark-cli（lark-doc）创作 / 编辑飞书云文档相关规范（署名约定 + docx 实操技巧）集中维护在领域规则文档 **`rules/lark.md`**：

- CC 端：`~/.claude/rules/lark.md`
- Codex 端：`~/.codex/rules/lark.md`

**触发条件**：本轮任务一旦涉及用 lark-cli 创作或编辑飞书云文档，**必须先把 `rules/lark.md` 读入上下文**，再开始动手。
