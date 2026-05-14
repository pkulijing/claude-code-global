# Development Constitution

所有项目都要遵循以下规则。

## 称呼

对话中的 CC 代表 Claude Code

## 核心开发模式

人类开发者与 Coding Agent 合作，分为需求 - 计划 - 执行 - 总结四步

### 开发模式详解

- 需求：结合当前现状，针对一个待解决的问题，给出明确详细的开发需求。人类主导，提供需求内容
- 计划：结合项目现状，分析需求，给出可行的详细计划。Agent 主导，人类 Review，**在 Plan 模式下输出**。
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

### 会话标题约定（CC 自身行为约束）

为方便 `/resume` 时通过会话标题历史快速定位特定开发轮次，CC 在开发轮次相关的对话中，**必须**在自己**第一条回复**的开头以 `Round N:` 前缀（N 为 `docs/N-*` 目录的数字编号）明确标注当前轮次，让 Claude Code 自动生成的会话标题以此为锚点。

- 示例：`Round 16: 多设备自动同步全局配置`
- 触发条件：通过 `/start <issue#>` 开新轮、或在已有 `docs/N-*` 目录下接续既有轮次（含读取/修改该目录下任何文档、或人类明确说要继续第 N 轮）
- 这是对 CC 自身行为的约束，无需人类提醒；CC 自己识别当前所处轮次并主动加前缀

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

## 项目本地推荐配置（由 stack 模板统一管理）

每个项目应配置一份与 `~/.claude/hooks/fix-after-edit.sh`（PostToolUse 自动 fix hook）输出对齐的本地工具链，避免「CC 编辑 → VS Code 保存触发 formatOnSave → 大 diff」的反复重排，并在 commit 前增加 lint 闸门。

**这些配置不再由各项目手动维护，而是通过 stack 模板统一管理：**

- 新项目 → `/bootstrap` 选 stack（如 `python-uv`），自动写入 `.prettierrc` / `.vscode/` / `.pre-commit-config.yaml` / `.gitignore` / `.github/workflows/lint.yml` / `pyproject.toml [tool.ruff]` 段、并生成 `.cc-template.yml` marker
- 已有老项目 → `/sync-project-config` 进入 adopt 模式补全
- 模板更新后 → 在项目目录跑 `/sync-project-config` 拉新（AI 智能 merge，per-file 用户决策）

每个 stack 模板包含的具体内容见 `~/.claude/templates/<stack>/`，schema 与设计见 `~/.claude/global-repo/docs/11-跨项目共享模板与sync-skill/`。

模板核心要素（python-uv stack 示例，其他 stack 各自约定）：

- `.prettierrc`：`{ "proseWrap": "preserve" }`，防止 prettier 强制换行中文长段落
- `.vscode/settings.json`：`[python]` / `[markdown]` 块的 `formatOnSave + defaultFormatter`（python 用 `charliermarsh.ruff`，markdown 用 `esbenp.prettier-vscode`）+ `editor.codeActionsOnSave: { "source.fixAll": "explicit", "source.organizeImports": "explicit" }`
- `.vscode/extensions.json`：推荐 `charliermarsh.ruff` / `esbenp.prettier-vscode` / `ms-python.python` 给协作者
- `.pre-commit-config.yaml`：commit 前 lint 闸门，`ruff-check` + `ruff-format`（不带 `--fix`）+ `pre-commit-hooks` 通用项
- `.github/workflows/lint.yml`：CI 兜底，跑 `ruff check` + `ruff format --check`
- `pyproject.toml` 的 `[tool.ruff]` 段：line-length / 选 rule 集 / format 风格

## Backlog 与开发项管理（Issue 驱动，GitHub / GitLab 双轨）

每个项目的开发项以 **issue 为真源**：详情、讨论、跨轮上下文都沉淀在 issue 里；`docs/BACKLOG.md` 退化为 **未关闭 issue 的扁平索引**，方便一眼看待选清单。

平台由 `git remote get-url origin` 自动判定 GitHub / GitLab —— 三件套 skill 不直接调 `gh` / `glab`，全部走 `~/.claude/scripts/platform_issue.py` helper（封装平台 dispatch + 字段归一）。

### 三轴 label

每条 issue 必须打三个 label，由 `_common` 模板的 `.github/labels.yml` 维护（schema 跨平台一致，GitLab 项目下也读同一份）：

- **`type:*`**：`feat` / `bug` / `refactor` / `perf` / `test` / `docs`（项目无关，全集统一）
- **`area:*`**：模块分类，**项目特异**（每个项目按自己模块改 labels.yml 中 `area:` 段）
- **`priority:*`**：`P0` 必须做、不做有重大风险 / `P1` 重大新功能 / `P2` 一般小功能

### Issue templates

`_common` 模板**双轨**提供：

- GitHub：`.github/ISSUE_TEMPLATE/{feat,bug,spike}.md`（frontmatter `labels:` 自动打 type label）
- GitLab：`.gitlab/issue_templates/{feat,bug,spike}.md`（首行 `/label ~"type:..."` quick action 自动打 type label）

两套同时落到所有项目（互不干扰，对端文件被平台忽略）。

### 三件套 skill 工作流

- **`/backlog`**：新增想法 → 走 issue template → 调 helper `issue-create` 含三轴 label → 自动在 `docs/BACKLOG.md` 对应 priority 段加一行链接
- **`/start <issue#>`**：开新轮 → 调 helper `issue-view` 拉详情（输出归一为 GitHub 风格 schema） → 写到 `docs/N-*/PROMPT.md` 顶部
- **`/finish`**：收尾 → SUMMARY.md → 在 commit message body 写 `Closes #<N>` → 从 BACKLOG.md 删对应那行

### Closes #N 与 git history 双向链接

commit/PR 描述里写 `Closes #N`，合并到 default branch 时**自动关 issue** —— GitHub 与 GitLab 均原生支持（GitLab 还支持 `Fixes` / `Resolves` / `Implements` 等更多关键词与 cross-project `Closes group/project#N` 引用）。issue 永久保留（含评论历史），与对应 commit/MR 双向可查 —— 这是把跨轮上下文从 BACKLOG 文件搬到 issue 后**最关键的可追溯保证**。

### 已完成 / 不再追踪

- 已完成项不在 BACKLOG.md 追踪，直接看 GitHub / GitLab closed issues
- BACKLOG.md 末尾「## 已完成 / 不再追踪」段记录**刻意决定不做**的项 + 原因（避免未来翻 SUMMARY 误以为遗漏）

## Python 开发规则

- 使用 uv 管理项目依赖，使用 `uv add` 添加依赖，在 `pyproject.toml` 中记录 (`uv add` 天然支持) 依赖列表，**禁止使用 `pip install` 或 `uv pip install`**
- 使用 `uv run` 运行 python 脚本，如 `uv run some_script.py`, `uv run python -m ruff xxxx`，**禁止直接调用 python 或 python3**
- 使用 ruff 做代码格式化和 python 语法检查
- pypi index指南：为了提高中国的下载速度，我们使用两个指定的源
  - 普通库从[清华源](https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple)下载
  - `torch/torchaudio/torchvision` 等 `torch` 相关的库从[aliyun镜像站](https://mirrors.aliyun.com/pytorch-wheels/cu121/) 下载. 你这个进程并不是一个完整的pypi源，需要使用 `extra` 方式在 `pyproject.toml` 中指定
  - `torch` 使用 2.5.1 版本，cu121
