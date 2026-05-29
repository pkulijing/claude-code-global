> 来自 [#11 Python 项目共享模板固化标准 src 布局 + uv 可编辑安装骨架](https://github.com/pkulijing/claude-code-global/issues/11)
> Labels: `type:feat` `priority:P2` `area:template`
>
> 来自 [#12 Python 开发风格 7 条沉淀建议：OO 偏好 / 绝对 import / 文件命名 / 注释纪律 / Protocol 鸭子型 / dict-of-dicts 信号 / 整合类覆盖盲区](https://github.com/pkulijing/claude-code-global/issues/12)
> Labels: （未打）

# 本轮开发需求

本轮一次性吃掉 #11 与 #12 两条 issue —— 它们都围绕"Python 开发模板"的优化展开，合并到同一轮可以让"项目模板"与"全局 Python 规范"的边界在一次改动里整理清楚，避免分两轮反复触碰同一批文件。

## 用户给出的总指引

1. **按 #11 修改 Python uv 项目模板**：把"标准 src 布局 + uv 可编辑安装"作为模板骨架固化下来，新建 Python 包就自动落到 `src/<pkg>/`，配套 hatchling build-system / pytest pythonpath / testpaths，免去每轮重复纠正。
2. **引入"子 CLAUDE.md 机制"**：把 #12 中沉淀的 7 条 Python 风格 / 工作流准则，连同当前 `GLOBAL_AGENTS.md` 里已有的 Python 开发规范，**整理到一个独立的 md 文件**作为 Python 相关的子 CLAUDE.md（领域规则文档），由 `GLOBAL_AGENTS.md` 顶层以指针方式引用、双轨部署到 CC（`~/.claude/`）与 Codex（`~/.codex/`）两端。

## 背景

两个 issue 的具体内容均已沉淀在 GitHub，要点摘录如下。

### #11：标准 src 布局 + uv 可编辑安装骨架

- **来源**：`wujie-data-format` 项目第 14 轮（mcap → LeRobot v2.1 转换器）新建 Python 包时把 `mcap2lerobot/` 平铺在仓库根，被用户当即纠正"遵循标准 src 布局"。是跨项目通用、每次新建 Python 包都会遇到的工程规范。
- **落点**：
  - 包目录 `src/<pkg>/`，不平铺在仓库根；
  - `pyproject.toml` 中配：
    - `[build-system]` 用 hatchling；
    - `[tool.hatch.build.targets.wheel] packages = ["src/<pkg>"]`；
    - `[tool.pytest.ini_options] pythonpath = ["src"]`、`testpaths = ["tests"]`；
  - `uv sync` 即可把本包装为可编辑安装，`python -m <pkg>` / 测试均可干净 import；
  - 顶层保留 `configs/`、`tests/` 与 `src/` 平级。

### #12：Python 风格 7 条 + 整合到全局 CLAUDE.md

来自一次 `wujie-data-format` 的代码 review session（非 `/start /finish` 闭环），针对 `mcap2lerobot` 包 OO 改造（5 文件改名 + 7 核心类抽离）过程中暴露的可复用 Python 风格 / 工作流准则。

**7 条要点**（原 issue 文本为准，本文档仅列标题）：

1. 偏好面向对象，避免"满文件 free functions"；
2. 包内绝对 import，单文件不混用风格；
3. 文件名 = 核心类名的 snake_case；
4. 注释 / docstring 写"当前真相"，不写"演化历史"（禁引 `round-XX` / `PLAN.md §X` / `issue #N`）；
5. 外部不可靠类型用 `Protocol` 鸭子型契约，配套禁防御性 `getattr`；
6. dict-of-dicts 是 OO 重构的强信号；
7. 整合类（编排器 / facade）必须至少 1 条 happy-path integration test。

**issue 落地建议**：分块加到全局 CLAUDE.md 的 Python 章节 / 文档记录规范 / TDD 小节。

## 范围与边界

- **In-scope**：
  - 改造 `templates/python-uv/` 模板使其默认产出 src 布局骨架（包目录 + pyproject 关键字段 + tests 目录）；
  - 新建领域规则文件，承载完整的 Python 开发规则（既包含 GLOBAL_AGENTS.md 中已有的 uv / ruff / pypi index / torch 规则，也包含 #12 的 7 条新规则）；
  - 改造 `GLOBAL_AGENTS.md`，把 Python 章节瘦身为"入口指针"并定义"子 CLAUDE.md 机制"的通用约定（为未来其他领域规则留出口子）；
  - 调整 `install.sh`，把新规则目录双轨部署到 `~/.claude/` 与 `~/.codex/`；
  - 同步更新 `bootstrap` / `sync-project-config` 等触发模板拷贝的 skill，使其正确处理新增模板文件（包括包名占位符如何注入）；
  - 同步更新本仓库 `CLAUDE.md`（项目级）中描述目录结构的段落。
- **Out-of-scope**：
  - 不把 #12 7 条规则机械翻倍复制到任何项目层的 CLAUDE.md；只在领域规则文件里维护一份，其他位置以指针 / 链接方式引用；
  - 不动 `templates/_common/`；本轮只触 `python-uv/`；
  - 不引入除 Python 外的其他领域规则文件（设计预留扩展位即可，落地交由后续 issue）。

## 待 PLAN 阶段决策的关键点

1. **"子 CLAUDE.md"在目录结构里的具体落位**：是 `rules/python.md`、`agent-rules/python.md`，还是 `CLAUDE.md.d/python.md`？需要权衡"语义清晰"vs"与 CC / Codex 原生 mention 机制兼容"。
2. **指针引用形式**：`GLOBAL_AGENTS.md` 是用 `@rules/python.md` mention（依赖 CC 主动解析）、纯文字指针（依赖 Agent 自觉读）、还是 install.sh 在合并时把内容内联展开？
3. **模板里的包名占位符**：标准 src 布局需要知道包名 `<pkg>`，而现有模板片段是无占位符的 raw 文件。需要决定走"`__pkg__/` 目录名 + bootstrap 时改名"、"`{{pkg}}` 字符串占位 + render"、还是"模板里只放 `src/` + 提示 bootstrap 自行建包目录"。
4. **整合 vs 增量**：现有项目（已经按旧布局生成）通过 `sync-project-config` 拉新模板时，src 布局这种"侵入性结构变更"是否要做？还是只对**新建**项目生效？
5. **#12 7 条的呈现粒度**：原文很长（含示例代码），子 CLAUDE.md 是 1:1 搬过来、还是要压缩成"规则 + 一句 Why + 一句 How"的紧凑形式？

## 验收

- `templates/python-uv/` 在 bootstrap 后可生成包含 `src/<pkg>/`、`tests/`、含 hatchling 配置的 `pyproject.toml` 的项目骨架，跑 `uv sync && uv run python -m <pkg> --help`（或等价 smoke）能通过；
- 任一项目下，CC 与 Codex 在进行 Python 任务时能感知到完整的 Python 规则（含原 4 条 + 新 7 条），方式是顶层 GLOBAL_AGENTS / AGENTS 文档明确指出"Python 任务请先读 `<子 CLAUDE.md 路径>`"；
- `install.sh` 双轨同步新规则文件，CC 端 `~/.claude/rules/python.md`（或最终路径）与 Codex 端 `~/.codex/rules/python.md` 都存在且内容一致；
- `GLOBAL_AGENTS.md` 原 Python 章节正文 ≤ 5 行（仅留指针 + 触发提示），细则全部下沉到子文件；
- 本仓库 `CLAUDE.md` 与 `docs/DEVTREE.md` 已反映新增的"规则文档"目录；
- 提交按 issue-driven 流程在 commit 中 `Closes #11` 与 `Closes #12`。
