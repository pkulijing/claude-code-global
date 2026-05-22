# SUMMARY

## 开发项背景

`GLOBAL_AGENTS.md`（全局宪法）通过 `install.sh` 软链为 `~/.claude/CLAUDE.md` 与 `~/.codex/AGENTS.md`，**每个项目、每次对话都会加载进上下文**。历经 round 10–22 多轮堆叠，文末几节被 AI 越写越细，把本应留在 skill / 模板 / docs 里的实现细节整段抄进了宪法，导致：

1. 常驻上下文里塞满低价值实现细节；
2. 「会话标题约定」一节要求 Agent 在首条回复加 `Round N:` 前缀，但该约定**从未真正生效**，需排查根因。

## 实现方案

### 关键设计 / 关键发现

- **会话标题约定为何失效（已实锤）**：Claude Code 的会话标题并非取自 assistant 首条回复文本，而是由独立的 `ai-title` 摘要器基于整段会话生成 —— 英文、随对话多次重算、不读首条回复。证据取自本仓库 transcript（`~/.claude/projects/.../*.jsonl` 的 `ai-title` 条目）：本轮回复开头确写 `Round 24:`，会话却被命名为 `Clean up global constitution file and review session titles`；历轮同理（`Debug number spacing...`、`python-uv bootstrap` 等），无一带 `Round N:`。**结论**：约定假设「标题来自首条回复」，该假设在 CC 上不成立，规则机制上无法落地。轮次定位本就由 `docs/N-*` 目录名承担。
- **「项目本地推荐配置」一节的考古**：起于 round 10（commit `3ea4718`）。当时把 format-after-edit hook 提到全局，但 `.prettierrc` 等配置 prettier 只从项目 cwd 找、全局下发不了，于是在宪法留一条「各项目自配」的兜底备忘。round 11 随即建了 stack 模板 + `/bootstrap` + `/sync-project-config` 自动下发机制，兜底备忘的使命即告结束，却只被改写成「指向新机制」而未删 —— 退化为纯指针，且与常驻 skill 列表里的信息重复。判定为冗余，整节删除。

### 开发内容概括

仅改 `GLOBAL_AGENTS.md` 一个文件（纯规范精简，无代码、无测试适用项）：

1. **删除**「会话标题约定」整节（失效约定）。
2. **精简**「Backlog 与开发项管理」（37 → ~7 行）：保留全部原则（issue 为真源、三轴 label、三件套分工、Closes #N、已完成不追踪），删实现细节（issue template 路径、helper schema 等）。
3. **删除**「项目本地推荐配置」整节（兜底备忘已被模板机制取代、与 skill 列表重复）。
4. **结构重组（用户主导）**：把精简后的 Backlog 内容改写为 `### 需求管理`，与 `### 需求生命周期` 并列收入 `## 核心开发模式`；四步总览句 + worktree 段上提为 `核心开发模式` 开篇，先给全景再展开。三轴 label 措辞收紧为「type 和 priority 的选项由 `_common` 模板维护」（area 项目特异，更准确）。

净效果：`GLOBAL_AGENTS.md` 159 → ~100 行，顶级章节从 7 个减到 6 个（称呼 / 核心开发模式 / git 规则 / 环境变量管理 / Python 规则）。Python、git、环境变量等硬约束章节未动。

### 额外产物

- 一段可复用的 transcript 取证方法：解析 `~/.claude/projects/<project>/*.jsonl` 中 `type=ai-title` 条目的 `aiTitle` 字段，可验证「会话标题实际由什么生成」。

## 局限性

- 历史 docs（round 20 / 22 的 SUMMARY / PLAN）中仍有对「会话标题约定」的归档记述，属历史记录，刻意不动。
- 三件套 skill（`/start` 等）经全仓搜索确认**无** `Round N:` 前缀残留指引 —— 该约定当初只活在宪法一处，删除即彻底，无连带清理。

## 后续 TODO

- 暂无强需求。若日后仍想要「会话标题可定位轮次」的能力，需走机制上可行的路径（如不依赖标题、靠 `docs/N-*` 目录或 transcript 搜索），而非约束首条回复文本。

## 可沉淀项

暂无。本轮属 claude-code-global 仓库自身的内容治理，结论（宪法精简原则、ai-title 取证法）已就地落在本仓库的宪法与本 SUMMARY 中，无需再向本仓库提跨项目 issue（自指守卫亦适用）。
