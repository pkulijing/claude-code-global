# PROMPT

## 需求

清理 `GLOBAL_AGENTS.md`（全局宪法）中冗余的内容。该文件通过 `install.sh` 链接为 `~/.claude/CLAUDE.md` 与 `~/.codex/AGENTS.md`，**会被每个项目、每次对话加载进上下文**，因此应只保留「原则 / 硬约束」，把可在 skill、模板、脚本里查到的实现细节移出去。

人类的初步判断：冗余主要集中在**最后几个章节**（均为 AI 在历轮陆续写入、越堆越细）。

此外，排查「会话标题约定（Coding Agent 自身行为约束）」这条规则为何没被遵守。

## 排查结论：会话标题约定为何无效（已查实）

宪法现有约定要求 Coding Agent 在「第一条回复的开头」加 `Round N:` 前缀，以便会话标题历史可定位轮次。

**根因**：Claude Code 的会话标题并非取自 assistant 的首条回复文本，而是由一个独立的 `ai-title` 摘要器基于整段会话内容生成，特征为：

- **英文输出**（与中文 `Round N:` 前缀无关）
- **多次重算**（随对话进展刷新，最终为全程摘要，非首条回复）
- 取自会话整体语义，**不读首条回复开头**

实锤（取自本仓库 transcript `~/.claude/projects/-Users-wujie-Personal-claude-code-global/*.jsonl` 中的 `ai-title` 条目）：

- 本轮回复开头确写 `Round 24:`，会话却被命名为 `Clean up global constitution file and review session titles`
- 历轮：`Debug number spacing in finish function`、`python-uv bootstrap`、`sync-project-config adopt path` —— 无一带 `Round N:`

即：这条约定假设「标题来自首条回复文本」，而该假设在 CC 上不成立，规则从机制上无法落地。不是 agent 不守规矩，是规矩本身无效。

## 目标

1. 精简宪法中冗余的实现细节章节，保留原则与硬约束，细节指向 skill / 模板 / docs。
2. 处置失效的「会话标题约定」章节（删除或重写为机制上可行的形式）。
