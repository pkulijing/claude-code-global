# Round 20：CC 与 Codex 双兼容调研

## 背景

本仓库（`claude-code-global`）目前的核心产物是为 Claude Code（下文沿用 CC）准备的：

- `GLOBAL_CLAUDE.md` → 通过 `install.sh` 软链到 `~/.claude/CLAUDE.md`，作为 CC 的全局 system prompt 注入入口
- `skills/` → CC 的 slash command（`/start` / `/finish` / `/commit` / `/backlog` 等）
- `hooks/` → CC 的 PostToolUse / SessionStart 等事件 hook
- `settings.base.json` → CC 的 settings 基线（permissions / hook 注册 / statusLine 等）

近期我（user）希望**同时使用 CC 和 Codex**（OpenAI 的 Coding Agent CLI / IDE 集成）。Codex 显然不会读 `CLAUDE.md`，它有自己的配置约定（如 `AGENTS.md`、`.codex/` 之类）。但**开发规范本身是工具无关的**——我希望两个 Agent 都能遵循同一份 Development Constitution，并尽可能复用相同的工作流（开新 round / commit / rebase / backlog 等）。

## 需求

调研「让本仓库的设置（至少 `CLAUDE.md` + `skills` + `hooks`）同时兼容 CC 与 Codex」的**可行性**和**实现方案**，产出一份调研报告（最终落到 `SUMMARY.md`）。

### 必须回答的问题

1. **Codex 的配置约定到底是什么**
   - Codex 用什么文件作为「全局指令 / project 指令」？（对应 CC 的 `~/.claude/CLAUDE.md` + 项目 `CLAUDE.md`）
   - 是否支持类似 slash command 的扩展机制？（对应 CC 的 `skills/`）
   - 是否支持 hook（PostToolUse / SessionStart 等事件钩子）？（对应 CC 的 `hooks/`）
   - settings / permissions 的等价物是什么？
   - 配置加载路径、文件名、frontmatter 格式有什么硬约束？

2. **CLAUDE.md 双兼容的可行路径**
   - 方案 A：Codex 直接读 `CLAUDE.md` —— 看 Codex 是否原生支持/可配置指向该文件
   - 方案 B：维护两份内容相同的文件（`CLAUDE.md` + `AGENTS.md` 等），通过软链或生成脚本同步
   - 方案 C：抽出 Agent 无关的 `CONSTITUTION.md`，CLAUDE.md / AGENTS.md 各自 include / 引用
   - 各方案的成本、维护性、是否会污染 CC 行为

3. **skills / hooks 的可移植性**
   - Codex 的 slash command 机制（若有）和 CC 的 skill（带 frontmatter 的 markdown + base directory）差异多大？
   - hook 接口（输入 JSON schema、stdout/stderr 协议、event 名称）是否有交集？
   - 若完全不兼容，是只兼容到「指令」层（让两个 Agent 读到相同的工作流描述）还是要做更深的 adapter？

4. **install.sh 的影响面**
   - 当前 `install.sh` 软链 `~/.claude/{CLAUDE.md,skills,hooks,scripts}` + 合并 `settings.base.json`。如果要同时支持 Codex，需要追加哪些步骤？
   - 是否引入 Codex 安装的检测（类似 `which codex`），按需安装？
   - scheduler 自动同步（`auto-update.sh`）是否需要感知 Codex 的存在？

### 范围边界

- **本轮只做调研，不写实现**。产出是「方案选型 + 实施 roadmap」，具体落地拆成后续 round（按 `/backlog` 入 issue）。
- 不需要等 CC 和 Codex 完全等价。可接受「90% 共享 + 10% 工具特有」的形态。
- 不需要解决双 Agent **同时**运行的协调问题（如同时写文件冲突）；本次只关心**配置层面的兼容**。

### 期望产出

`SUMMARY.md` 应包含：

1. Codex 配置约定的全景图（基于官方文档 / 社区资料调研）
2. 与本仓库现有结构的字段级对照表（`CLAUDE.md` ↔ ?、`skills/` ↔ ?、`hooks/` ↔ ?、`settings.base.json` ↔ ?）
3. 至少 2 个可行方案，列清各自的成本、收益、风险
4. 推荐方案 + 实施 roadmap（拆成几个 follow-up issue）

## 备注

- 工作目录使用独立 worktree（已进入 `round-20-codex-cc-compat`），避免污染 master
- 调研可能涉及 WebFetch / WebSearch 查 Codex 官方文档，注意核对版本（Codex 还在快速迭代）
