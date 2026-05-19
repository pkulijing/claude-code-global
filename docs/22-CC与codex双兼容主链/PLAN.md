# Round 22 实现计划：CC 与 Codex 双兼容主链（#1-#4）

## 总体策略

方案 A —— 仓库内容保持**单一真源**，所有产物单份；`install.sh` 是唯一感知 agent 差异的层。本轮按 issue #8 依赖顺序落 #1→#2→#3→#4。

---

## #1 `GLOBAL_CLAUDE.md → GLOBAL_AGENTS.md` 改名 + Agent-neutral 改写

### 1.1 文件改名

`git mv GLOBAL_CLAUDE.md GLOBAL_AGENTS.md`

### 1.2 正文中性化改写（在 `GLOBAL_AGENTS.md` 内）

| 位置                                    | 现状                                                       | 改为                                                                                                                                                     |
| --------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 「称呼」段                              | 「对话中的 CC 代表 Claude Code」                           | 增补 Codex：CC = Claude Code，Codex = OpenAI Codex，本文统称二者为 **Coding Agent**                                                                      |
| 核心开发模式·计划步                     | 「**在 Plan 模式下输出**」                                 | 「先撰写 `PLAN.md` 等人类确认后再写代码（CC 用 PlanMode；Codex 用户可配 `--sandbox read-only --ask-for-approval on-request` 加固，指令本身已足够约束）」 |
| 「会话标题约定（CC 自身行为约束）」标题 | `CC 自身行为约束`                                          | `Coding Agent 自身行为约束`                                                                                                                              |
| 该段正文 3 处 `CC`                      | 「CC 在...」「让 Claude Code 自动生成...」「这是对 CC...」 | 统一改 `Coding Agent`；「Claude Code 自动生成的会话标题」→「Coding Agent 自动生成的会话标题」                                                            |
| 项目本地推荐配置段                      | 「CC 编辑 → VS Code 保存触发 formatOnSave」                | 「Coding Agent 编辑 → VS Code 保存...」                                                                                                                  |

> `~/.claude/hooks/fix-after-edit.sh` 等路径**保留不动** —— 依赖 #4 把 `~/.codex/` 侧软链到同结构。

### 1.3 改名传播（消除悬空引用）

`GLOBAL_CLAUDE.md` 字面量在以下**活文件**出现，全部同步改为 `GLOBAL_AGENTS.md`：

- `install.sh`（#4 一并重构，见下）
- `README.md`（仅改文件名引用；新增双兼容段是 #7，不在本轮）
- `CLAUDE.md`（项目根，目录结构说明段）
- `skills/bootstrap/SKILL.md`

> `docs/**` 下的历史 PROMPT/PLAN/SUMMARY 是**冻结记录**，不改。

---

## #2 skills body 9 处 CC-specific 字符串中性化

### 2.1 `AskUserQuestion`（8 处）→ 自然语言「询问用户」

CC 读到「询问用户，让用户在 X/Y/Z 中选一个」仍会触发 native `AskUserQuestion`；Codex 走等价的 `RequestUserInputQuestion`。逐处改写：

| 文件                                  | 行  | 改写要点                                           |
| ------------------------------------- | --- | -------------------------------------------------- |
| `skills/backlog/SKILL.md`             | 34  | 「询问用户，让其在 `feat`/`bug`/`spike` 中选一个」 |
| `skills/backlog/SKILL.md`             | 50  | 「询问用户从 area 列表中选一条」                   |
| `skills/backlog/SKILL.md`             | 54  | 「询问用户选 `P0`/`P1`/`P2`」                      |
| `skills/bootstrap/SKILL.md`           | 82  | 「询问用户，让其在以下选项中选一个」               |
| `skills/bootstrap/SKILL.md`           | 132 | 「先询问用户确认是否执行」                         |
| `skills/devtree/SKILL.md`             | 43  | 「询问作者确认 / 调整」                            |
| `skills/sync-project-config/SKILL.md` | 185 | 「询问用户：列出可选 stack 让其选一个」            |
| `skills/sync-project-config/SKILL.md` | 216 | 「先询问用户确认是否执行」                         |

保留每处的语义（默认值、选项内容、warn 文案）不变，只去掉硬绑的工具名。

### 2.2 「进入计划模式」（1 处）

`skills/start/SKILL.md:28`：「进入计划模式，撰写 `PLAN.md` 并请用户确认」
→ 「起草 `PLAN.md`，请用户确认后再开始写代码」

> skills body 中的 `$HOME/.claude/scripts/...` 路径硬编码**保留** —— #4 会把 `~/.codex/scripts/` 软链到同处。

---

## #3 新增 `codex.config.base.toml`

仓库根新增一份 TOML 基线，镜像 `settings.base.json` 的两块语义。

### 3.1 hooks 注册

Codex 在 `~/.codex/config.toml` 用 `[[hooks.<Event>]]` 段注册 hook，事件名与 CC 同名（`SessionStart` / `PostToolUse`）。base 内容：

```toml
# >>> claude-code-global managed >>>  (此 marker 块由 install.sh 整体重写，勿手改)

[[hooks.SessionStart]]
command = "bash $HOME/.codex/scripts/auto-update.sh --session"
# matcher = "startup"  # Codex 若不支持 matcher 则由脚本自身判定
timeout = 60

[[hooks.PostToolUse]]
matcher = "Edit|Write"
command = "bash $HOME/.codex/hooks/fix-after-edit.sh"
timeout = 30

# <<< claude-code-global managed <<<
```

### 3.2 permissions / sandbox profile

Codex 用 `approval_policy` + `sandbox_mode` 取代 CC 的 `permissions.allow/deny`。base 给一组与 CC「日常可写、敏感操作问一下」对齐的默认值：

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"
```

> **未决依赖**：Codex 0.130.0 的 `[[hooks.*]]` 精确字段（是否支持 `matcher` / `timeout`、stdin schema）Round 20 未实测。本轮按最合理形态写，并在 SUMMARY 标注「字段精确性待 #8 实测校正」。`fix-after-edit.sh` 脚本本体本轮**不动**（字段 fallback 留 #8）。

---

## #4 `install.sh` 双轨重构

### 4.1 目标行为

- 跑一次 `bash install.sh`：检测 `~/.claude/` 和 `~/.codex/` **各自是否存在**，对存在的一侧部署，缺哪侧跳过哪侧（不报错）。
- CC 侧行为与现状**完全等价**（不退化）。

### 4.2 重构方式

把现有「针对 `TARGET_DIR` 的一串 link/merge」抽成一个函数 `deploy_agent <agent-home> <main-doc-target-name> <settings>`，对两个 agent home 各调一次：

| 产物            | CC（`~/.claude/`）                    | Codex（`~/.codex/`）                           |
| --------------- | ------------------------------------- | ---------------------------------------------- |
| 主指令文档      | `CLAUDE.md` → `GLOBAL_AGENTS.md`      | `AGENTS.md` → `GLOBAL_AGENTS.md`               |
| `skills/`       | 逐子目录软链                          | 逐子目录软链                                   |
| `hooks/`        | 逐文件软链                            | 逐文件软链                                     |
| `scripts/`      | 逐文件软链                            | 逐文件软链                                     |
| `templates/`    | 整目录软链                            | 整目录软链                                     |
| `global-repo`   | 软链仓库根                            | 软链仓库根                                     |
| settings/config | merge `settings.base.json`（JSON/jq） | merge `codex.config.base.toml`（TOML，见 4.3） |

检测逻辑：`[ -d "$HOME/.claude" ]` / `[ -d "$HOME/.codex" ]`；若两端都不存在 → warn 并退出。

### 4.3 TOML 合并（`merge_toml`）

`settings.base.json` 的合并靠 jq 递归；TOML 没有 jq。采用 **marker 块整体重写**策略（比逐键 merge 简单且稳健，且本仓库管理的就是一整块）：

- base 文件用 `# >>> claude-code-global managed >>>` / `# <<< ... <<<` 包裹托管块。
- `merge_toml <base> <dst>`：
  - dst 不存在 → 直接 `cp`。
  - dst 存在且无 marker 块 → 末尾追加托管块（先备份 `.bak.<ts>`）。
  - dst 存在且有旧 marker 块 → 用 base 的块**整体替换**旧块（先备份）。
  - 块内容与现有一致 → 跳过（不产生空备份）。
- 用户在 marker 块**外**手写的 TOML 永远保留。

> 实现用 `awk` 做块替换（标准工具，macOS/Linux 通用），不引入 TOML 解析器。

### 4.4 收尾提示

`install.sh` 末尾若部署了 Codex 侧，打印醒目提示：

> ⚠️ Codex hooks 首次需进入 Codex 跑一次 `/hooks` 命令 review 后才会生效。

### 4.5 scheduler 调用

`scheduler/install.sh` 在 #6 一并改造（见下）。

---

## #5 `.cc-template.yml → .agent-template.yml`

项目侧 marker 文件改名。该 marker 由 `/bootstrap` 写入、`/sync-project-config` 读写，标识「本项目已接入跨项目模板」。

### 5.1 字符串改名

`.cc-template.yml` 字面量在以下活文件出现，全部改为 `.agent-template.yml`：

- `skills/bootstrap/SKILL.md`（Step 3.6 写 marker、echo-back 清单 —— 行 166/168/191）
- `skills/sync-project-config/SKILL.md`（行 9 normal sync 说明、行 33 模式判断、行 293 回写 —— 及其它出现处）
- `README.md`（跨项目共享模板段）
- `GLOBAL_AGENTS.md`（#1 改名后的主指令文档，「跨项目共享配置」段）

### 5.2 sync skill 旧名自动迁移

`/sync-project-config` 的「模式判断」段（读项目根 marker 决定 Normal sync / Adopt）增加一步**旧名迁移**，置于读取 marker **之前**：

- 若项目根存在旧名 `.cc-template.yml` 且不存在新名 `.agent-template.yml` → 用 `git mv .cc-template.yml .agent-template.yml` 重命名（非 git 仓库已被前置检查拦掉，必走 git），并向用户明确告知「检测到旧版 marker 文件名，已自动迁移为 `.agent-template.yml`」。
- 若两者都存在 → 报冲突、停止，请用户手动处理（不猜测）。
- 迁移后照常按新名 `.agent-template.yml` 进入 Normal sync。

> bootstrap 是新建项目，直接写新名，无迁移问题。

---

## #6 `auto-update.sh` 与 `scheduler/` 用 `$AGENT_HOME` 变量化

目的：让自动同步机制不再硬绑 `~/.claude/`，Codex-only 机器也能正常落日志 / 节流戳。

### 6.1 `scripts/auto-update.sh`

- 顶部加 `AGENT_HOME="${AGENT_HOME:-$HOME/.claude}"`。
- `LOG_DIR` / `STAMP_FILE` 改用 `$AGENT_HOME` 派生（`$AGENT_HOME/logs`、`$AGENT_HOME/.auto-update-last-run`）。
- 脚本自定位 `REPO_DIR`（解析自身软链）逻辑**不变** —— 不论从 `~/.claude/scripts/` 还是 `~/.codex/scripts/` 软链调用都能定位仓库根。
- `bash "$REPO_DIR/install.sh"` 调用不变 —— install.sh（#4 后）一次跑就双轨部署，无需各 agent 各跑一遍。

### 6.2 SessionStart hook 命令

- CC 侧（`settings.base.json`）：命令保持 `bash $HOME/.claude/scripts/auto-update.sh --session`，`AGENT_HOME` 走默认值 `~/.claude`。
- Codex 侧（`codex.config.base.toml`，#3 产出）：命令前置 env —— `AGENT_HOME=$HOME/.codex bash $HOME/.codex/scripts/auto-update.sh --session`，使 Codex session 的同步日志/节流戳落到 `~/.codex/`。

### 6.3 `scheduler/`

OS 调度器（launchd / systemd user timer）本身 agent 无关。本轮调整：

- `scheduler/install.sh`：检测存在的 agent home（`~/.claude` / `~/.codex`），选定一个作为调度器的 `AGENT_HOME`（优先 `~/.claude`，仅 Codex 时取 `~/.codex`）—— 因为 `auto-update.sh` 一次跑即双轨部署，**只需注册一个**调度器，无需双 timer 制造重复 pull。
- `systemd.service.template` / `launchd.plist.template`：注入 `AGENT_HOME` 环境变量（systemd 用 `Environment=`，launchd 用 `EnvironmentVariables` dict），并把日志路径里的 `~/.claude/logs` 改为 `{{AGENT_HOME}}/logs`。
- `render_template` 增加 `{{AGENT_HOME}}` 占位符替换。

> 这是对 roadmap「双装时跑两遍」的有意偏离：install.sh 单跑即双轨部署，再注册第二个 timer 只会重复 pull 同一仓库。决策与理由记入 SUMMARY。

---

## #7 README 增「同时支持 CC 与 Codex」段

`README.md` 更新（不改写已有 round 历史描述，只做双兼容增补）：

1. **新增独立章节**「## 同时支持 Claude Code 与 Codex」，置于「工作原理」之后，含：
   - 设计：单一真源 + `install.sh` 双轨部署；`AGENTS.md` 是跨工具事实标准
   - 双装方式：`install.sh` 自动检测 `~/.claude/` 与 `~/.codex/`，缺哪端跳哪端
   - 部署对照表（CC `~/.claude/` ↔ Codex `~/.codex/`，主指令文档 / skills / hooks / scripts / settings⇄config.toml）
   - known limitations：Codex hooks 首次需 `/hooks` review；`disable-model-invocation` frontmatter 容忍度待实测（#8）；`fix-after-edit.sh` stdin schema 待实测
2. **就地修订**已有段落中因本轮改名而过期的字面量：
   - 标题/正文 `GLOBAL_CLAUDE.md` → `GLOBAL_AGENTS.md`（含 GitHub 链接 URL）
   - `.cc-template.yml` → `.agent-template.yml`
   - 「工作原理」表与「多设备自动同步」表中纯 `~/.claude/` 表述补一句「Codex 端对应 `~/.codex/`」或泛化，避免误导

---

## 测试策略

`install.sh` 是与文件系统/外部工具集成的脚本，按宪法「集成类可先实现跑通再补测」执行；核心验证用**手动可重复 checklist**：

1. `merge_toml` 三分支单独验证：
   - 临时目录造一个**无** `~/.codex/config.toml` 的场景 → 应 `cp`。
   - 造一个含用户自定义 TOML 但无 marker 块 → 应追加块且保留用户内容。
   - 造一个含旧 marker 块 → 应整块替换、用户块外内容不动。
2. 双轨幂等：连跑两次 `install.sh`，第二次所有项应报「已跳过」。
3. CC 侧不退化：`~/.claude/` 下 `CLAUDE.md` / `skills/` / `settings.json` 与本轮前一致（软链目标对、settings 含基线）。
4. Codex 侧软链全部生成、`~/.codex/config.toml` 含 marker 块、`~/.codex/AGENTS.md` 软链正确。
5. `git mv` 后全仓搜索确认无残留 `GLOBAL_CLAUDE.md` / `.cc-template.yml` 悬空引用（排除 `docs/`）。
6. `auto-update.sh` 用 `AGENT_HOME` 跑一次烟测：`AGENT_HOME=/tmp/fake-agent bash scripts/auto-update.sh` 日志/戳应落到 `/tmp/fake-agent/`。

> 端到端「在 Codex 里跑 `/start` `/finish` 等」属 issue #8 的 #8 子项，不在本轮。

## 风险与回滚

- `git mv` + 多文件改名：若有遗漏引用，靠测试步骤 5 全仓搜索兜底。
- TOML marker 块策略未在真实 Codex `config.toml` 上验证字段语义 —— 本轮只保证「文件结构正确、merge 幂等」，字段精确性待 #8。
- `.cc-template.yml` 改名是项目侧破坏性变更：本仓库自身是「无 stack 只 `_common`」项目，根目录现无 `.cc-template.yml`（确认后再改名），其它已接入项目靠 sync skill 的旧名自动迁移兜底。
- 回滚：本轮纯仓库内改动 + `install.sh` / `auto-update.sh` 行为变更，`git revert` 即可；`install.sh` 对已存在文件均先 `.bak` 备份。

## 落地顺序

1. #1 `GLOBAL_CLAUDE.md` 改名 + 改写 + 传播
2. #2 skills 9 处中性化
3. #5 `.cc-template.yml` 改名 + sync 旧名迁移（与 #2 同属 skill 改字符串，并轨做）
4. #3 新增 `codex.config.base.toml`
5. #6 `auto-update.sh` + `scheduler/` 的 `$AGENT_HOME` 变量化
6. #4 `install.sh` 双轨重构（`deploy_agent` + `merge_toml`，依赖 #3/#6 产物）
7. #7 README 双兼容段 + 改名字面量修订
8. 跑测试 checklist + `bash install.sh` 在本机实跑一次验证双轨
