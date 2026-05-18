# Round 20：CC 与 Codex 双兼容调研 — SUMMARY

> 调研日期：2026-05-19。本机已实测的 Codex 版本：`codex-cli 0.130.0` (npm `@openai/codex`)；CC 版本：`2.1.119`。

---

## 1. 背景

本仓库（`claude-code-global`）原本完全为 Claude Code (CC) 设计：

- `GLOBAL_CLAUDE.md` → 软链 `~/.claude/CLAUDE.md`（CC 全局指令）
- `skills/<n>/SKILL.md` → 软链 `~/.claude/skills/`（CC slash command）
- `hooks/fix-after-edit.sh` → 软链 `~/.claude/hooks/`（CC PostToolUse 钩子）
- `settings.base.json` → 合并进 `~/.claude/settings.json`（CC permissions + hooks 注册）

现 user 同时使用 OpenAI Codex CLI，希望本仓库**单一真源**地同时为两端服务，避免维护两套漂移。

调研目标在 `PROMPT.md` 中明确：(a) 摸清 Codex 配置约定全景；(b) 给字段级对照表；(c) 至少两个可行方案；(d) 推荐方案 + 实施 roadmap。

---

## 2. 关键发现

### 2.1 Codex 配置约定（本机实测 + 二进制 strings 验证）

| 维度                       | CC                                                                                           | Codex                                                                                                                                                   | 证据来源                                                                                                                                                             |
| -------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **全局指令**               | `~/.claude/CLAUDE.md`                                                                        | `~/.codex/AGENTS.md`                                                                                                                                    | Codex 二进制内置 base instructions 含 `# AGENTS.md spec` 段；strings 显示 "discover AGENTS.md docs for instruction sources"                                          |
| **项目指令**               | `<repo>/CLAUDE.md` + 嵌套合并                                                                | `<repo>/AGENTS.md` + 嵌套合并                                                                                                                           | 同上；Codex 沿 cwd → root 路径逐层拼接                                                                                                                               |
| **Slash command 路径**     | `~/.claude/skills/<n>/SKILL.md`                                                              | `~/.codex/skills/<n>/SKILL.md` 或 `$CODEX_HOME/skills/<n>/SKILL.md`                                                                                     | 本机 `ls ~/.codex/skills/.system/` 实见 5 个内置 skill（`skill-creator`/`skill-installer`/`plugin-creator`/`imagegen`/`openai-docs`）                                |
| **Skill frontmatter**      | `name` / `description` / `disable-model-invocation`                                          | `name` / `description` / `metadata` (含 `short-description` 等) / 可选 `allowed_tools` / `when_to_use` / `arguments`                                    | 实读 `~/.codex/skills/.system/skill-creator/SKILL.md` 等多份                                                                                                         |
| **Hook 事件名**            | `SessionStart` / `UserPromptSubmit` / `PreToolUse` / `PostToolUse` / `Stop` / `Notification` | **同名**：`SessionStart` / `UserPromptSubmit` / `PreToolUse` / `PostToolUse`                                                                            | strings 显示 `PreToolUseHookSpecificOutputWire`、`PostToolUseHookSpecificOutputWire`、`SessionStartHookSpecificOutputWire`、`UserPromptSubmitHookSpecificOutputWire` |
| **Hook 注册**              | `settings.json` 中声明性配置                                                                 | `~/.codex/config.toml` 中 `[[hooks.*]]` 段；**首次跑须经 `/hooks` 命令手动 review**                                                                     | 二进制有 "hooks need review before they can run. Open /hooks to review them"                                                                                         |
| **Hook stdin/stdout 协议** | JSON stdin / JSON stdout / exit code                                                         | JSON stdin / JSON stdout / exit code（`*HookSpecificOutputWire`）                                                                                       | 命名约定一致；具体字段需进一步实测                                                                                                                                   |
| **Settings / config**      | JSON：`~/.claude/settings.json`                                                              | TOML：`~/.codex/config.toml`                                                                                                                            | 本机 `cat ~/.codex/config.toml` 实见                                                                                                                                 |
| **Permissions 模型**       | `permissions.allow/deny` + 工具 ACL                                                          | `--sandbox <read-only/workspace-write/danger-full-access>` + `--ask-for-approval <untrusted/on-request/never>`，可在 `config.toml` 中固化               | `codex --help`                                                                                                                                                       |
| **结构化询问 API**         | `AskUserQuestion` tool                                                                       | `RequestUserInputQuestion`（带 `Option` + `label`）                                                                                                     | strings 显示 `RequestUserInputQuestion`/`QuestionOption`/`label`，与 CC `AskUserQuestion` 概念等价                                                                   |
| **Plan mode 等价**         | `EnterPlanMode` 工具 + `Shift+Tab Tab`，harness 强制 read-only + `ExitPlanMode` 批准门       | **无单一内建模式**，组合等价：`--sandbox read-only` + `--ask-for-approval on-request`；交互中用 `/permissions` 切换；用户自行约束"写代码前先出 PLAN.md" | `codex --help`；plan slash 在 0.130.0 中未内见，但 sandbox + approval 双开足以达到等价行为                                                                           |
| **MCP**                    | 同                                                                                           | 同（在 `config.toml`，本机有 `codex mcp` 子命令）                                                                                                       | `codex --help`                                                                                                                                                       |
| **Plugin**                 | 实验中（CC plugin 仓库尚未稳定）                                                             | 内建：`codex plugin` 子命令 + `plugin-creator` 系统 skill                                                                                               | `codex --help`、本机系统 skill                                                                                                                                       |
| **CLI 检测**               | `command -v claude`                                                                          | `command -v codex`                                                                                                                                      | 本机均通过                                                                                                                                                           |

### 2.2 AGENTS.md 作为跨工具事实标准

`AGENTS.md` 已成多家 Agent 共同采纳的开放标准（Codex / Cursor / Aider / Amp / Windsurf / Roo / VS Code Agent 等）。CC 当前用 `CLAUDE.md`，但**社区共识做法**是软链 `CLAUDE.md → AGENTS.md`，使一个 markdown 文件同时为两类工具服务。本调研未实测 CC 是否会原生读 `AGENTS.md`（未来如读，则可省软链）。

### 2.3 修正之前的子 agent 误判

初次探索时一个子 agent 把"skill body 提到 `AskUserQuestion` 工具名"判为"绑死 CC harness"，给出"11 个 skill 仅 3 个可移植"的结论。经 user 反馈后**直接读 skill body 验证**，发现：

- `AskUserQuestion` 全仓库出现 8 次，全部是「让用户在 X/Y/Z 中选一个」结构化询问——而 Codex **同样有** `RequestUserInputQuestion` 结构化询问 API；改成自然语言「询问用户」表述，CC 仍会用 native tool 触发，Codex 也会用其等价机制
- `EnterPlanMode` / `Skill(` 在 skill body 里**0 引用**（子 agent 凭空脑补）
- `进入计划模式` 仅在 `/start` 1 处——可改写为中性表述
- 真正硬耦合的只有：(a) `~/.claude/` 路径硬编码，(b) `.cc-template.yml` 文件名，(c) `disable-model-invocation` frontmatter 字段（CC 私有）

**修正后判断**：仓库内容 **~85% 是 Agent-neutral 工作流**，CC 耦合主要在**包装层**（install 路径 / 文件名 / settings schema），不在**内容层**。

### 2.4 仓库耦合度对照表（修正版）

| 组件                        | 实际可移植度 | 真实耦合点                                                                                                                                                                  |
| --------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GLOBAL_CLAUDE.md`          | **~85%**     | 3 段引用 CC 概念（「CC 称呼」「会话标题约定」「执行前必须 ... 进入**计划模式**」）                                                                                          |
| 11 个 skills body           | **~90%**     | (a) 8 处 `AskUserQuestion` 工具名提及（可改"询问用户"），(b) 1 处「进入计划模式」，(c) 多处 `~/.claude/{templates,scripts,global-repo}` 路径，(d) `.cc-template.yml` 字面量 |
| `hooks/fix-after-edit.sh`   | **~95%**     | 脚本本体（jq+ruff+prettier）100% 通用；耦合在事件注册侧，CC/Codex 都用 `PostToolUse` 事件                                                                                   |
| `settings.base.json`        | **0%**       | CC 私有 JSON schema；需新增 `codex.config.base.toml` 镜像                                                                                                                   |
| `scripts/auto-update.sh`    | **~70%**     | 业务通用，但硬编码 `~/.claude/logs/`、`~/.claude/global-repo`                                                                                                               |
| `scripts/platform_issue.py` | **~95%**     | 平台无关，仅依赖 `$HOME/.claude/scripts/` 路径                                                                                                                              |
| `install.sh`                | **需重构**   | 仅做 CC 软链 + settings merge                                                                                                                                               |
| `scheduler/`                | **~100%**    | OS-level（launchd / systemd），Agent 无关                                                                                                                                   |

---

## 3. 字段级对照表（实施层）

| CC 现状                                              | Codex 等价                                                                   | 实施动作                                                                                  |
| ---------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `~/.claude/CLAUDE.md` ← 软链 `repo/GLOBAL_CLAUDE.md` | `~/.codex/AGENTS.md` ← 软链 `repo/GLOBAL_AGENTS.md`                          | 改名仓库文件，install.sh 双轨软链                                                         |
| `~/.claude/skills/<n>/SKILL.md`                      | `~/.codex/skills/<n>/SKILL.md`                                               | install.sh 把 `repo/skills/` 同时软链到两处                                               |
| `~/.claude/hooks/fix-after-edit.sh`                  | `~/.codex/hooks/fix-after-edit.sh`（或单一脚本被两端 config 各自 reference） | 软链一份，CC settings.json + Codex config.toml 各自注册一次                               |
| `~/.claude/settings.json` (JSON)                     | `~/.codex/config.toml` (TOML)                                                | 两端各一份 base 配置文件，分别合并                                                        |
| `disable-model-invocation: false` (frontmatter)      | 未识别字段，**实测预期被忽略**                                               | 暂保留；如 Codex 报错再剔除（见 §6 未决项）                                               |
| `~/.claude/scripts/platform_issue.py` 硬编码         | 软链 `~/.codex/scripts/platform_issue.py` → 同一处                           | install.sh 双轨；skill body 用 `$HOME/.claude/scripts/` 或 `${AGENT_HOME:-$HOME/.claude}` |
| `.cc-template.yml` marker（项目侧）                  | 改名 `.agent-template.yml`                                                   | bootstrap / sync-project-config skill 改字符串；老项目首次 sync 时识别旧名自动迁移        |
| `EnterPlanMode` 工具触发 + `ExitPlanMode`            | `--sandbox read-only` + `--ask-for-approval on-request`，或纯指令约束        | skill body 表述中性化即可（"先写 PLAN.md 等用户确认再写代码"）                            |
| `AskUserQuestion` 工具名                             | `RequestUserInputQuestion`（语义等价）                                       | 改写为"询问用户"，两端各按 native 工具落实                                                |

---

## 4. 方案对比

### 方案 A（推荐）：单一真源 + 双轨 install

仓库内容**实质保持单一真源**，靠 (1) 几处改名 + (2) `install.sh` 重构为双轨软链 + (3) 新增一份 `codex.config.base.toml` 镜像 settings 实现双兼容。

**收益**：

- 维护成本 ≈ 不变（仅多一份 settings 镜像和一份 install 检测分支）
- 单一真源不破坏
- AGENTS.md 与社区共识对齐
- 未来新增 skill 一份即落两端

**代价**：

- 中等粒度破坏性变更（`GLOBAL_CLAUDE.md` 改名、`.cc-template.yml` 改名、install.sh 重构）
- skill body 9 处文字微调
- 需新增 ~50 行 TOML 配置文件

### 方案 B（备选）：完全独立两套

`~/.claude/` 与 `~/.codex/` 各维护一套，互相 fork。**否决**：基于 §2.4 修正后判断（85% 内容通用），方案 A 已足够；方案 B 反让 single-source-of-truth 报废。

### 方案 C（讨论但否决）：放弃 CC，全迁 Codex

`AGENTS.md` 是社区标准，CC 已能通过软链支持；user 短期不愿放弃 CC。**否决**。

---

## 5. 推荐方案 A 的实施 Roadmap（每条可直接 `/backlog` 起 issue）

按依赖顺序：

1. **[refactor] `GLOBAL_CLAUDE.md` → `GLOBAL_AGENTS.md` + Agent-neutral 改写**
   - 改文件名
   - 「称呼」段：CC 加 Codex 同义
   - 「会话标题约定（CC 自身行为约束）」 → 「Coding Agent 自身行为约束」
   - 「执行前必须 ... 进入计划模式」 → 「执行前必须先撰写并确认 PROMPT.md 和 PLAN.md（CC 用 PlanMode；Codex 用户可配 `--sandbox read-only --ask-for-approval on-request` 增加 harness 保障，但指令本身已足够约束）」
   - `priority: P1`，`area: doc`

2. **[refactor] skills body 9 处 Agent-neutral 化**
   - 8 处 `AskUserQuestion` → "询问用户，让用户在以下选项中选一个"
   - 1 处「进入计划模式」 → 「起草 PLAN.md 并等用户确认后再写代码」
   - 路径硬编码 `~/.claude/scripts/...` → 保留（依赖 install.sh 把 `~/.codex/scripts/` 软链到同处）
   - `priority: P1`，`area: skill`

3. **[feat] 新增 `codex.config.base.toml`**
   - 镜像 `settings.base.json` 的 hooks 注册段（`[[hooks.PostToolUse]]` 注册 `fix-after-edit.sh`）
   - permissions profile（`[permissions.default]` 默认 workspace-write + ask-for-approval=on-request；可考虑 `:read-only` profile 供"安全模式"）
   - 注意 Codex hooks **首次需 `/hooks` review** 后才生效
   - `priority: P1`，`area: install`

4. **[feat] `install.sh` 双轨重构**
   - 检测 `~/.claude/` 存在 → 部署 CC 端（如现状）
   - 检测 `~/.codex/` 存在 → 部署 Codex 端：
     - `~/.codex/AGENTS.md` → repo `GLOBAL_AGENTS.md`（软链）
     - `~/.codex/skills/` → repo `skills/`（软链）
     - `~/.codex/hooks/` → repo `hooks/`（软链）
     - `~/.codex/scripts/` → repo `scripts/`（软链）
     - `~/.codex/templates/` → repo `templates/`（软链）
     - `~/.codex/global-repo` → repo `.`（软链）
     - `~/.codex/config.toml` ← 合并 `repo/codex.config.base.toml`
   - 均不强制；缺哪个就只装哪个
   - `priority: P1`，`area: install`

5. **[refactor] `.cc-template.yml` → `.agent-template.yml`**
   - bootstrap / sync-project-config skill 内字符串改名
   - sync 流程在见到旧名 marker 时自动重命名（破坏性迁移走一轮）
   - `priority: P2`，`area: template`

6. **[refactor] `auto-update.sh` 与 `scheduler/` 用 `$AGENT_HOME` 变量化**
   - 默认 `~/.claude`；可由调度器 env 覆盖
   - 双装时跑两遍（CC 和 Codex 各一次）
   - `priority: P2`，`area: install`

7. **[docs] README 增「同时支持 CC 与 Codex」段**
   - 双装方式、`AGENTS.md` 标准说明、known limitations（hooks 需 review）
   - `priority: P2`，`area: doc`

8. **[test] 双装端到端验证**
   - 在 Codex 中跑 `/start` / `/finish` / `/commit` / `/devtree`，对照 CC 行为
   - 记录 frontmatter `disable-model-invocation` 是否被 Codex 拒绝
   - `priority: P1`，`area: test`

---

## 6. 局限性 & 未决项

1. **未实测 `disable-model-invocation` frontmatter** — Codex 0.130.0 对未知 frontmatter 字段是否报错未验证。如报错，需在 skills 中改字段名或加 sync 过滤。预期被忽略（Codex 自身 skill 也有自定义 `metadata.*` 字段）
2. **未实测 Codex hooks 协议细节** — stdin JSON 字段名是否与 CC 完全对齐（如 `tool_input` vs `tool_call`）。`fix-after-edit.sh` 现读 `.tool_input.file_path`，若 Codex 字段名不同需在脚本里加分支或写 wrapper
3. **Hooks 首次需 `/hooks` review** — 与 CC 的"settings.json 声明即生效"行为不同；install.sh 跑完后需提示用户**首次进 Codex 跑一次 `/hooks` 批准**
4. **CC 是否原生读 `AGENTS.md`** — 未实测。若读，install.sh 可省 `~/.claude/CLAUDE.md` 软链；若不读则继续靠软链
5. **`AGENTS.md` 32 KiB 上限** — 本仓库 `GLOBAL_CLAUDE.md` 当前约 6 KiB，远低于；但项目侧未来加深嵌套时需要监控
6. **`fix-after-edit.sh` 在 Codex 端实测未做** — 一致性高度依赖 stdin JSON schema 完全对齐；保守做法是 hook 脚本里加 `tool_input // tool_call` fallback
7. **plan slash 等价方案不强约束** — Codex 没有 harness 强制 read-only 模式，仅靠 sandbox flag + 用户自约束。若 user 习惯 PlanMode 的强模式语义，需要在 GLOBAL_AGENTS.md 中明确"在 Codex 端建议用 `--sandbox read-only` 启动 round"

---

## 7. 后续 TODO

- 把 §5 的 8 条 roadmap 用 `/backlog` 起 issue（建议先起 #1-#4 这条主链）
- 跑一次"穷举式 Codex 实测":
  - 在 `~/.codex/AGENTS.md` 放一份 `GLOBAL_CLAUDE.md` 副本，启动 codex 看是否被 base instructions 拼上
  - 在 `~/.codex/skills/test-skill/SKILL.md` 放一份含 `disable-model-invocation: false` 的 SKILL，看 Codex 是否报错或忽略
  - 在 `~/.codex/config.toml` 注册一个 echo hook 到 `PostToolUse`，看 stdin JSON 实际 schema
  - 若任一不符预期，更新本 SUMMARY §6 局限性段并调整 roadmap
- **可选研究方向**：CC 仓库 issue #7（plugin 化改造）若真落地，整个双兼容方案可能简化为"两端各装一个 plugin"——届时 install.sh 大幅瘦身。本轮先按当前 skills 形态做兼容；后续 plugin 化后重新评估

---

## 8. 关键设计

1. **AGENTS.md 作为锚点**：把 `GLOBAL_CLAUDE.md` 改名 `GLOBAL_AGENTS.md` 不是单纯文件改名，而是**对齐跨工具事实标准**，让本仓库直接吃上 AAIF 生态红利
2. **install.sh 双轨而非两份目录**：仓库不分裂为 `for-cc/` 和 `for-codex/`，所有产物单份；install.sh 是唯一感知 agent 差异的层。这保住单一真源、不污染日常迭代
3. **skill body 工具名中性化**：CC 的 `AskUserQuestion` 与 Codex 的 `RequestUserInputQuestion` 概念等价；改成自然语言「询问用户」后 CC 仍会触发 native tool（描述文本就够），Codex 也走自己的等价 API，**两端都不破坏**
4. **Plan mode 不强求 harness 等价**：仅靠 system prompt 中"先写 PLAN.md 等确认"已能让两端 agent 都遵守这套节奏；Codex 用户额外用 `--sandbox read-only` 是 opt-in 加固，不是必须
5. **`disable-model-invocation` 暂不处理**：基于"Codex 对未知 frontmatter 字段宽容"的预期保守保留；万一报错再剔
