# Coding Agent 全局配置（Claude Code + Codex）

通过 GitHub 仓库**单一真源**地管理 Claude Code 与 OpenAI Codex 两个 coding agent 的全局配置（`GLOBAL_AGENTS.md` / `skills/` / `hooks/` / `scripts/` / `scheduler/` / `settings.base.json` / `codex.config.base.toml` / `user.config.example.env` / `uv.config.base.toml`）、「跨项目共享开发配置模板」（`templates/`）和「领域规则文档」（`playbooks/`，按 `<topic>.md` 拆分语言 / 栈 / 流程细则，由 GLOBAL_AGENTS.md 顶层指针引用），支持多设备同步与跨项目复用。`install.sh` 双轨部署到 `~/.claude/` 与 `~/.codex/`，缺哪端就只装哪端，详见下文「同时支持 Claude Code 与 Codex」。多设备自动同步（无需手动 `git pull && bash install.sh`）见下文「多设备自动同步」。

开发流程遵循 [`GLOBAL_AGENTS.md`](https://github.com/pkulijing/claude-code-global/blob/master/GLOBAL_AGENTS.md) 中定义的「需求 → 计划 → 执行 → 总结」四步模式，开发项以 issue 为**单一真源**（GitHub / GitLab 双轨自动判定，无本地索引文件，详见下文「开发项管理」）。

## 工作原理

Claude Code 读取 `~/.claude/`、Codex 读取 `~/.codex/` 下的全局配置。本仓库通过 `install.sh` 双轨部署到两端（软链接 / 合并）。下表以 Claude Code 端为例，Codex 端结构对称（见「同时支持 Claude Code 与 Codex」）：

| 仓库文件                  | 部署到                                                 | 方式                                | 说明                                                                                                                                                                                    |
| ------------------------- | ------------------------------------------------------ | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GLOBAL_AGENTS.md`        | `~/.claude/CLAUDE.md`（Codex 为 `~/.codex/AGENTS.md`） | 软链接                              | 修改仓库即修改实际配置，`git pull` 即完成同步                                                                                                                                           |
| `skills/*/`               | `~/.claude/skills/*/`                                  | 软链接（逐个子目录）                | 不影响 `~/.claude/skills/` 下不属于本仓库的 skill                                                                                                                                       |
| `hooks/*`                 | `~/.claude/hooks/*`                                    | 软链接（逐个文件）                  | hook 脚本本体；由 `settings.base.json` 中带 `# @claude-code-global:<name>` 标记的条目以绝对路径引用                                                                                     |
| `scripts/*`               | `~/.claude/scripts/*`                                  | 软链接（逐个文件）                  | 被 SKILL.md 显式调用的稳定脚本（如 `platform_issue.py`），SKILL.md 通过 `$HOME/.claude/scripts/...` 引用                                                                                |
| `templates/`              | `~/.claude/templates/`                                 | 软链接（整目录）                    | 跨项目共享开发配置模板源，由 `/bootstrap` `/sync-project-config` 读取                                                                                                                   |
| `playbooks/`              | `~/.claude/playbooks/`                                 | 软链接（整目录）                    | 领域规则文档（按 `<topic>.md` 拆，如 `python.md` / `frontend.md`），由 GLOBAL_AGENTS 顶层指针引用，Agent 命中触发条件时主动 Read。**目录名不能改叫 `rules`**——那是 CC 保留目录，见下方说明        |
| `agents/`                 | `~/.claude/agents/`（**仅 CC 端**）                    | 软链接（整目录）                    | 子 agent 定义（`review-orchestrator` / `code-reviewer` / `code-reviewer-deep`），frontmatter 钉死 `model` + `effort`，**让 `/review-loop` 编队不继承主会话的思考档**。Codex 无此概念故不链         |
| 仓库根目录                | `~/.claude/global-repo/`                               | 软链接                              | 让 `/sync-project-config` 通过 stable 路径访问模板的 git 历史，计算模板版本变化                                                                                                         |
| `settings.base.json`      | `~/.claude/settings.json`                              | **合并**（非破坏性）                | 本机特有设置保留；仅追加/覆盖基线里声明的项                                                                                                                                             |
| `user.config.example.env` | `~/.claude-code-global/config.env`                     | **seed**（user-wins，非软链非合并） | 仓库内是示例基线；真实配置在仓库外、`git pull`/自动同步不覆盖；只在用户未设时填默认、新增 key 才补缺追加。详见 [docs/27-用户可配置项机制/DESIGN.md](docs/27-用户可配置项机制/DESIGN.md) |
| `uv.config.base.toml`     | `~/.config/uv/uv.toml`                                 | **seed**（user-wins，缺失才创建）   | 推荐的系统级 uv 配置：默认 `python-preference = "only-managed"`（让 uv 全权管 python、规避系统 python 缺 `Python.h` 致 C 扩展编译失败）+ 清华源默认 index；已有该文件不覆盖             |
| `scheduler/`              | （不部署）                                             | 由 `install.sh` 末尾消费            | 渲染模板后写到 `~/Library/LaunchAgents/`（macOS）或 `~/.config/systemd/user/`（Linux），注册自动同步调度器                                                                              |

`settings.json` 之所以不软链接，是因为它通常既含跨机共享设置（如 `permissions.allow`），又含本机特有偏好（如 `effortLevel`）。合并规则：

- **object**：递归合并
- **array**：并集去重（如 `permissions.allow` 会把仓库基线里的条目追加进本地已有的列表，而不是覆盖）
- **scalar**：仓库基线胜出；不想跨机共享的标量就别写进 `settings.base.json`
- 多次运行 `install.sh` 幂等；真正发生变化时会先备份成 `settings.json.bak.<timestamp>`

合并依赖 `jq`（macOS 自带 `/usr/bin/jq`；Linux 各发行版用包管理器安装）。

### 为什么领域规则目录叫 `playbooks/` 而不是 `rules/`

**`~/.claude/rules/` 是 Claude Code 的保留目录**：放进去的 `.md` 会被当作**用户级 memory 全文注入每一个会话的系统提示**，无论项目类型、无论是否相关。这与本仓「宪法只留指针表、Agent 命中触发条件才 Read」的设计意图正好相反。

本仓早期正是软链到了那个名字，八份领域文档因此每会话常驻——实测代价 **36,520 token/会话**（`~/.claude/rules/` 挂载时 64,821 token，改挂 `~/.claude/playbooks/` 后 28,301 token）。改用 CC 不认识的中性目录名后，加载完全由宪法指针表 + 显式 Read 驱动。**别改回去。** 来龙去脉见 [docs/51-rules按需加载/](docs/51-rules按需加载/)。

**推论**：往 `~/.claude/` 下新增任何目录前，先确认该名字不是 CC 保留名。已知保留：`rules` / `skills` / `agents` / `commands` / `hooks` / `plugins` / `workflows` / `themes` / `plans` / `tasks` / `teams` / `projects` / `sessions` / `cache` / `backups` / `debug`。本仓的 `scripts/` / `templates/` / `playbooks/` 经核查均非保留名。

`install.sh` 会自动清理老机器上遗留的 `~/.claude/rules` 与 `~/.codex/rules` 旧软链（仅当它确实指向某个本仓 checkout 时才删；用户自建的真实目录、指向别处的软链一律不碰）。

## 同时支持 Claude Code 与 Codex

本仓库**单一真源**地服务 Claude Code (CC) 与 OpenAI Codex 两个 coding agent：skills / hooks / 主指令文档单份维护，`install.sh` 双轨软链到两端，新增 skill / 改 hook 不用写两遍。

设计依据：`AGENTS.md` 已是多家 agent 共同采纳的跨工具事实标准（Codex / Cursor / Aider / Windsurf 等），仓库内容约 85% 本就 agent-neutral，CC 耦合主要在包装层（安装路径 / settings schema）而非内容层。因此把全局规范文档命名为 `GLOBAL_AGENTS.md`，软链为 CC 的 `CLAUDE.md` 与 Codex 的 `AGENTS.md`。

`install.sh` 自动检测 `~/.claude/` 与 `~/.codex/` 各自是否存在（agent 自身安装时会创建其 home 目录），对存在的一侧部署，缺哪端就跳过哪端：

| 仓库产物                                                          | Claude Code（`~/.claude/`）                         | Codex（`~/.codex/`）                                            |
| ----------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------------------- |
| 主指令文档                                                        | `CLAUDE.md` ← `GLOBAL_AGENTS.md`                    | `AGENTS.md` ← `GLOBAL_AGENTS.md`                                |
| `skills/` `hooks/` `scripts/` `templates/` `playbooks/` `global-repo` | 软链                                                | 软链                                                            |
| `agents/`（子 agent 定义）                                        | 软链                                                | **不链** —— Codex 没有子 agent 定义这个概念                     |
| 配置基线                                                          | `settings.json` ← 合并 `settings.base.json`（JSON） | `config.toml` ← 合并 `codex.config.base.toml`（TOML marker 块） |

Codex 端配置基线 `codex.config.base.toml` 镜像 `settings.base.json` 的 hook 注册（`PostToolUse` 自动 fix）。合并策略：`config.toml` 不存在则整份复制；已存在则只注入 / 整体替换 `# >>> claude-code-global managed >>>` … `# <<< … <<<` 之间的 marker 块，块外用户内容（`approval_policy` / `[projects]` 等）一律保留。

**已知限制**：

- Codex hooks 首次需进入 Codex 跑一次 `/hooks` 命令 review 后才生效（`install.sh` 跑完会打印提示）。
- skill body 中 `$HOME/.claude/scripts/...` 等路径仍硬编码；双装机器上 `~/.claude/` 始终存在故无碍，纯 Codex 机器尚未适配。
- skill frontmatter 的 `disable-model-invocation` 字段、`fix-after-edit.sh` 读取的 hook stdin JSON 字段名在 Codex 端的容忍度 / 一致性待端到端实测（见 issue #8）。

## 安装

```bash
git clone <repo-url> ~/Developer/claude-code-global
bash ~/Developer/claude-code-global/install.sh
```

重复执行 `install.sh` 是安全的（幂等），不会影响 `~/.claude/skills/` 下不属于本仓库的 skill。

## GLOBAL_AGENTS.md 内容概览

`GLOBAL_AGENTS.md` 定义了所有项目通用的开发规范：

| 模块                      | 内容                                                                                                                                                                                                                                                 |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **核心开发模式**          | 需求 → 计划 → 执行 → 总结的四步协作流程，每个开发项在 `docs/` 下留档（PROMPT.md / PLAN.md / SUMMARY.md）；每轮默认在独立 git worktree 内进行，支持多轮并行                                                                                           |
| **git 规则**              | 中文 semantic commit message，AI 提交须带 Co-authored-by（按执行 Agent 选身份：CC → `Claude` / Codex → `OpenAI Codex`），`.gitignore` 按目录拆分                                                                                                     |
| **环境变量管理**          | `.env.local`（真实值，gitignore）+ `.env.example`（占位符，提交），禁止泄露密钥                                                                                                                                                                      |
| **领域规则文档**          | 语言 / 栈 / 流程的具体细则下沉到 `playbooks/<topic>.md`（CC 端 `~/.claude/playbooks/`、Codex 端 `~/.codex/playbooks/`）；本宪法只保留"指针 + 触发条件"，**这些文件默认不在上下文里**，Agent 命中条件时必须在动手前主动 Read                                    |
| **Python 开发规则**       | 指针到 [`playbooks/python.md`](playbooks/python.md)：uv 管依赖 / ruff / pypi index（清华 + aliyun pytorch-wheels）/ src 布局 + uv_build（含 hatchling、多包 workspace 两个 escape hatch）/ Python 风格细则 / 测试约定                                        |
| **Python 打包发布规则**   | 指针到 [`playbooks/python-packaging.md`](playbooks/python-packaging.md)：含前端产物的成员 wheel 化（hatchling + `artifacts` glob）/ 自托管 GitLab Registry 两坑（`UV_SYSTEM_CERTS` + `--check-url` 不兼容）/「同版本号不覆盖」的两个形态（`pip install --target` 与 `uv tool install`）/ 应用内更新自检骨架 / 装进隔离目录与正式版并存                       |
| **前端开发规则**          | 指针到 [`playbooks/frontend.md`](playbooks/frontend.md)：npm 走 npmmirror / Biome（前端的 ruff）/ React 19 + Vite 6 + TS strict / tailwind v4 CSS-first / shadcn-ui / 落 `frontend/` 子目录，与后端正交                                                      |
| **ROS 2 开发规则**        | 指针到 [`playbooks/ros2.md`](playbooks/ros2.md)：colcon 工作空间（包落 `src/`）/ ament_cmake + ament_python / package.xml format 3 / CMakeLists ament-first（依赖消费三步法 + 导出 + install 路径）/ 纯逻辑 / ROS 薄壳分层 / 新增包检查清单                  |
| **lark-cli 文档创作规则** | 指针到 [`playbooks/lark.md`](playbooks/lark.md)：lark-cli 创作飞书云文档默认加署名行（`⚡ Crafted with lark-cli · <YYYY-MM-DD>`）+ docx 实操技巧（署名落位 / 媒体置顶 / 内容文件相对路径）                                                                   |
| **飞书 bot 后端规则**     | 指针到 [`playbooks/feishu-bot.md`](playbooks/feishu-bot.md)：lark-oapi 长连接 at-least-once 送达 → 按 `message_id` / `event_id` 幂等去重（线程安全 + 有界，附最小骨架）+ 卡片回调 `card.action.trigger` 需在开发者后台配「接收回调」订阅，否则点击无任何回调 |
| **LLM 应用开发规则**      | 指针到 [`playbooks/llm-app.md`](playbooks/llm-app.md)：接 LLM 前先分清「多步 Agent」（执行结果会回传给模型，此时只返回第一个 tool_call 是正确行为；回传的具体形态随 provider 而异）与「一次性任务拆分」（无第二轮，必须换成单 tool + `steps` 数组），错配会**静默漏步**且只在「有依赖的请求」上翻车 + 实测符合率对照（错配 5% / 75%，改结构后 95% / 100%；调参与只改 prompt 措辞都救不回来）+ LLM 组件单测必须统计性、不能用 fake 替模型作答                                                                                       |
| **Shell 脚本开发规则**    | 指针到 [`playbooks/shell.md`](playbooks/shell.md)：写含中文 / 全角字符的 bash 脚本两个固定坑（双引号串内中文注释禁字面 `"`、`$var` 紧贴 CJK 一律 `${var}`）+ 只在远端 / CI 跑的脚本必须配本地沙盘测试 + 非交互式执行（ssh / 定时器 / CI）不继承 profile、PATH 里没有 `~/.local/bin` + 给用户手动执行的长命令一律写成脚本                                                                                                  |
| **云端 Routine 环境规则** | 指针到 [`playbooks/cloud-routine.md`](playbooks/cloud-routine.md)：claude.ai Routines 云端 sandbox 实测能力矩阵（gh 未装 / REST 403 / 仓库 CLAUDE.md 才进系统提示 / 无输出回路）+ 指令 / 工具链 / 平台能力三层组合推荐                                       |
| **定时无头 Agent 规则**   | 指针到 [`playbooks/scheduled-agent.md`](playbooks/scheduled-agent.md)：**本机**定时唤起无头 agent（launchd / systemd timer + `claude -p`）的四层架构（OS 定时器 / wrapper / 无头 agent / 确定性脚本）+ macOS·Linux 差异速查 + 实战坑清单（宿主唯一权威副本 / PATH 显式 export / 最小 allowedTools / 通知回路闭环） |
| **开发项管理**            | issue 为**单一真源**（GitHub / GitLab 自动双轨），三轴 label（`type:*` / `area:*` / `priority:*`），三件套 skill：`/backlog` `/start` `/finish`；无本地索引，open 项速览走按 priority 过滤的 saved query                                             |
| **跨项目共享配置**        | `templates/_common/` + stack 模板（如 `python-uv`）由 `/bootstrap`（新项目）和 `/sync-project-config`（老项目 adopt / 拉新）统一管理                                                                                                                 |

## Skills

基线 `settings.base.json` 中预置了 `permissions.allow: ["Skill(*)"]`，让所有 slash command 默认放行，避免反复弹权限确认。

本仓库提供以下 skill。`/backlog` `/start` `/finish` 三件套配合 `/commit` 形成完整的「issue 驱动」开发闭环；小到「改个函数、说清楚即可」的改动走轻量流 `/quick`（不落 docs、不开 worktree、不进计划模式，直接改 → 自动 commit）；其余按需调用。执行阶段 Agent 自主判断开发单元完成即 `/commit` 收口，**每次 commit 前自动经 `/review-loop`**（委派独立 context 的 orchestrator 子 agent 并行扇出多个独立 reviewer 角度，置信过滤 + 探针验证；发现高置信正确性问题就修、跑测试+happy-path 验证、复审，迭代到「运行验证通过 + 无高置信 correctness 问题」才放行；2 轮不收敛自动留痕放行）——人类 review 前移到 `/finish`，面对的是每个 commit 都已过独立 review 的干净分支。**编队规格的单一真源是 `/review-loop` skill 与 `agents/*.md`，此处不复述。**

| Skill                  | 用途                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/backlog`             | 把一条想法走 issue templates 创建成 issue（GitHub / GitLab 自动判定，含三轴 label）—— issue 即单一真源，不写任何本地索引                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `/start`               | 开新一轮开发：**先与远端对齐**（`git fetch` + 查目标 issue 是否已被做掉：issue 自身 `state` / 已合入的关闭 commit / 远端在途分支三个信号，命中就停下报告让人拍板），再建独立 git worktree（`.claude/worktrees/round<N>-<英文短描述>`，**整串纯 ASCII、短描述 `[a-z0-9-]` 且 ≤ 20 字符**——GitHub 网页端导航不进非 ASCII 分支名的文件树）+ 同名分支、建 `docs/<编号>-<描述>/`、撰写 PROMPT.md，进入计划模式撰写 PLAN.md 等用户确认后再写代码。轮次编号取**五源并集**（本树 docs / 本地在途分支 / 其它 worktree / 远端已合入 docs / 远端在途分支），避免多设备并行撞号；远端对齐的三条失败路径（无 origin / fetch 失败 / issue 拉不到）一律只提示不阻断。支持 `#<issue 号>` / GitHub or GitLab issue URL（推荐），也支持自由描述；`--no-worktree` 跳过 worktree 在当前分支直接干                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `/finish`              | 收尾本轮：撰写 SUMMARY.md → 反思跨项目可沉淀流程（任意项目都跑，逐条确认后可直接向 claude-code-global 跨仓库提 issue） → 关联并关闭 issue（如有 `Closes #N`，GitHub / GitLab 均原生支持；「刻意不做」项归档为带 `wontfix` 的 closed issue） → `/devtree` → 必要时同步 README → `/commit` → worktree 轮自动收尾（rebase → FF 合并主分支 → 二次确认后清理 worktree/分支/tag，不自动 push）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `/quick`               | 轻量开发流（三档里最轻）：不落 docs / 不开 worktree / 不进计划模式，直接改代码 → 自动 `/commit` 收尾。默认当前分支直接改，`--branch` 切轻量分支 `quick/<ascii 短描述>`，`#<issue>` 会拉 issue 详情指导改动（详情只进上下文、不落文档）+ 收尾带 `Closes #N`。适合「小函数改一下、说清楚即可」的小改；要文档追踪 / 计划讨论走 `/start`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `/routine-dev`         | 云端 routine 的真逻辑：扫本仓 open issue → **两条通道**分诊（**自动通道**保守判、只许落文档；**标记通道**认 owner 打的 `auto:take` label，落点放开到 `skills/`（除自己）/ `templates/` / `scripts/` / `hooks/`）→ 按落点与主题**合批**（不是一 issue 一 PR）→ 每条走 `/quick` 形态开发（一条一个 commit、各带 `Closes #N`）→ 每批一个 PR。四条红线绝不因标记放宽：自己 / `agents/` / `install.sh` / `.github/`。**分诊结论会回写成 `auto:skip` 缓存起来**，下次不再读那些 issue 的正文（被人编辑 / 评论后自动失效）。由 claude.ai Routines 每周一 / 三 / 五定时调用，本机可 `--dry-run` 试跑；无人值守下所有「停下问用户」的分岔都有明确契约。**曾名 `/routine-docs`**。详见下文「issue 的自动开发」                                                                                                                                                                                                                                                                                                                                        |
| `/routine-slim`        | 云端 routine：按**增长阈值**触发（`context_budget.py delta --threshold 15`，比 4 周前涨超 15% 才动手，否则空转退出），把指令面按**三板斧**精简一轮并出 PR。三板斧 = 已有单一真源的重复表述去重（留指针）／成组同向细则上提为一句判断原则／事故 WHY 的过程叙事压成结论一句；**明确不做 ablation 删除**。**只允许「搬走」不允许「蒸发」**——PR 描述强制三列表格（删了什么 / 依据哪条判据 / 现在从哪读得到）+ `check-refs` 零失效引用。安全边界：`GLOBAL_AGENTS.md` 与本仓 `CLAUDE.md` **只报告不动手**，永不碰自己 / `/routine-dev` / `agents/` / `.github/` / `install.sh` / `scripts/` / `hooks/` / `templates/` / `docs/`。每周日 01:00 UTC 定时，本机可 `--dry-run` 试跑。详见下文「指令面的定期精简」 |
| `/commit`              | 分析当前变更，自动生成中文 semantic commit message 并提交，末尾按执行 Agent 附加 Co-authored-by（CC → `Claude` / Codex → `OpenAI Codex`）；**提交前自动内嵌 `/review-loop`**（委派独立 context 子 agent 编队 review，迭代到「运行验证通过 + 无高置信 correctness 问题」才落 commit）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `/review-loop`         | 提交前的自动 review 迭代环。**收敛靠「运行验证 + 高置信过滤」，非 reviewer 挑不出为止**——治三个实战病根（挑刺变慢、把基础功能审废、一次 review 烧光 session）。主路径：委派**独立 context 的 review orchestrator 子 agent**（不复用开发 context，不依赖 CC 内置 `/code-review`——其 `disable-model-invocation` 随版本漂移），按档位并行扇出 3 个（默认）/ 5 个（并发/多线程/跨进程重试/状态机/难复现/跨 3+ 模块 diff）独立 reviewer 角度，跨 reviewer 去重 + 0–100 置信打分（<80 过滤）+ 探针验证，返回单一 finding 列表。**编队的模型与思考档由 `agents/*.md` 钉死、不继承主会话**（主会话跑 xhigh 时编队不跟着烧）。**三要素并闸收敛**：(A) 运行验证（受影响测试全绿 + happy-path 主流程跑通，编排器无测先补；排在 reviewer 意见之前，堵「基础功能审废无人知」）+ (B) 无高置信 correctness finding（只认 file:line 证据+真会触发，pre-existing/pedantic/推测 corner case 不阻断）+ (C) 已定前提未被重复质疑。修复走 TDD 正序（先写会红的复现测试再改实现）；2 轮不收敛自动留痕放行（REVIEW.md + commit 标注，人工兜底在 `/finish`），全程无人在环。**委派本身已获宪法长期授权**（平台通用指令里形如 "unless the user requested it" 的条件式限制，其条件在本工作流下已满足，见 `GLOBAL_AGENTS.md`）。降级有**硬门槛**：只有**能力缺失**才算委派失败（策略约束一律不算），且**必须实际核验过**——真发起一次并失败，或核对确认工具不在列表；留痕须附失败证据，**编造一次没发生的调用来凑证据同样禁止**。配置/指令文件不跳过，仅纯用户文档/注释才跳过。由 `/commit` 提交前自动调用，也可手动跑 |
| `/bootstrap`           | 为空项目搭建文档骨架（README / CLAUDE / DEVTREE）+ 选 stack 铺设跨项目模板，仅在项目首次开发前调用一次                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `/sync-project-config` | 把本仓库管理的「跨项目共享开发配置模板」最新变化同步进当前项目；含 adopt 模式（无 marker 老项目首次接入）+ 废弃 BACKLOG.md 一次性迁移（老项目遗留 `docs/BACKLOG.md` 时引导迁云端 issue 后删除）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `/triage`              | 盘点当前仓库 open issue，按 **priority × scope** 二维打一张排序表（issue 号 / priority / scope 档 / area / 自动化状态 / 一句话）并给**一条**下一轮推荐 + 摊开的依据。「自动化」列标出 `auto:take`（routine 会做）与 `auto:skip`（routine 已放弃、**只可能由人来做**，同等条件下更该排前面）。scope 优先读 issue 正文现成的 scope 字段，模型现估的加 `?` 后缀、估不出标「未填」，**不许猜一个填进去**。三条硬约束：只读无副作用（不改 issue、不自动 `/start`）/ 走 `platform_issue.py issue-list` 不直调 `gh` `glab` / 不落任何本地索引。不取代 saved query，只在「要挑下一轮」时跑一次                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `/devtree`             | 依据 `docs/DEVTREE.md` 中作者维护的 Epic 结构，重新生成可视化图表和节点索引                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `/rebase`              | 诊断本地分支分叉并按清单引导完成 rebase，历史保持 FF 直线                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `/pybump`              | 升级 Python 项目版本号（`pyproject.toml`），提交并打 tag                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## Hooks

`hooks/` 下放跨项目共用的 hook 脚本，由 `install.sh` 软链到 `~/.claude/hooks/`，并由 `settings.base.json` 中的 hook 条目以绝对路径 `$HOME/.claude/hooks/...` 引用。

| Hook                | 触发时机                  | 作用                                                                                                                                                       |
| ------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fix-after-edit.sh` | PostToolUse（Edit/Write） | 编辑后自动跑项目本地工具链（如 `ruff check --fix`、`prettier --write`），让 AI 改动跟项目 formatter 输出对齐，避免 VS Code 保存时 formatOnSave 触发大 diff |

由本仓库管理的 hook 条目以 `# @claude-code-global:<hook-name>` 注释作为身份标记；`install.sh` 通过这个标记做集合差分（增 / 删 / 同名替换），不影响用户手动添加的 hook。

## Scripts

`scripts/` 下是被 SKILL.md 显式调用的稳定脚本（非 hook、非 skill），由 `install.sh` 软链到 `~/.claude/scripts/`，SKILL.md 通过绝对路径 `$HOME/.claude/scripts/<name>` 引用。

| Script              | 用途                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `platform_issue.py` | 跨平台 issue / label / repo helper：封装 `gh` ↔ `glab` 双轨调用，按 `git remote get-url origin` 自动 dispatch。被 `/backlog` `/start` `/finish` `/triage` `/bootstrap` `/sync-project-config` 调用；`issue-view` 归一输出含 `state` / `stateReason`（两端只有 `open` / `closed` 两值，判据挂在两端词形一致的 `closed` 上，判不出一律算 `open`；`stateReason` 为 GitHub 独有，区分「做完了」与「有人决定不做」，供 `/start` 开轮远端对齐消费）；`issue-list` 列 open issue（归一 json 数组，schema 与 `issue-view` 一致，供 `/triage` 消费）；`issue-comment` 给 issue 补材料（两端连子命令名都不同：`gh issue comment --body-file` ↔ `glab issue note -m`，长正文走 argv 不经 shell 故无需转义；GitLab 侧取不到 URL 时只 warn 不报错，因为评论已发出）；`issue-create` 支持 `--repo` 跨仓库提 issue（配合 `--platform`，供 `/finish` 把可沉淀项提到 claude-code-global）——跨仓库创建强制带 ≥1 个 `--label`（零 label 直接拒绝，确需裸提才加 `--allow-no-label`），`label-list` 亦支持 `--repo` 以便创建前校验目标仓库 label。零第三方依赖（仅 stdlib），含 `--self-test`。完整契约（dispatch / color 转换 / exit 2/3/4 降级）见同目录 [`platform_issue.md`](scripts/platform_issue.md)，多个 skill 引用此单一真源 |
| `context_budget.py` | 指令面预算量化，零第三方依赖（仅 stdlib）。`measure` 出每文件字符 / token / 常驻-懒加载分类；`delta --since <ref>` 与历史版本比增长率（**基线由 git 历史算出，不落状态文件、不打 tag**），`--threshold` 供 routine 当闸；`check-refs` 校验跨文件引用可达性，是「只允许搬走不允许蒸发」的机械兑现。被 `/routine-slim` 调用。**token 估算系数由 CC `/context` 实测标定**（中文按英文经验值 4 字符/token 估会低估约 3 倍），换模型或大改文风后需重新标定；单测 41 项在 [`docs/52-指令面精简与定期化/test_context_budget.py`](docs/52-指令面精简与定期化/test_context_budget.py) |
| `user-config.sh`    | 用户可配置项的可 source 库：`ccg_seed_user_config`（user-wins seed，缺省才填/补缺追加）、`ccg_read_config`（安全解析，不 blind `source`）、`ccg_apply_git_default_branch`。被 `install.sh` source，未来 hook/skill 可复用。详见 [docs/27-用户可配置项机制/DESIGN.md](docs/27-用户可配置项机制/DESIGN.md)                                                                                                                                                                                                                                                                                                                                            |
| `auto-update.sh`    | 多设备自动同步主脚本：跑 `git fetch` → ff-only `git pull` → `bash install.sh`，由 OS 调度器（launchd/systemd）触发，30min 节流。详见下文「多设备自动同步」                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

### 私有化部署 GitLab 的 glab 证书问题

如果 `glab auth login` 报错形如 `x509: certificate signed by unknown authority` 或 `tls: failed to verify`，多半是私有化部署的 GitLab 用了自签或内部 CA 签发的证书。**永久修复**（不要用 `skip_tls_verify` 类降级方案）：把服务器证书加到系统信任库。

1. 抓证书：

   ```bash
   openssl s_client -showcerts -connect your-gitlab-host.com:443 </dev/null 2>/dev/null \
     | openssl x509 -outform PEM > gitlab.crt
   ```

2. 加到系统信任库：
   - **macOS**：打开 Keychain Access → 把 `gitlab.crt` 拖进 **System** keychain → 双击该证书 → Trust 段设为 **Always Trust**
   - **Linux (Ubuntu/Debian)**：
     ```bash
     sudo cp gitlab.crt /usr/local/share/ca-certificates/
     sudo update-ca-certificates
     ```

加完后重新 `glab auth login` 即可。

## 跨项目共享模板

`templates/` 下维护「跨项目共享开发配置模板」，由 `install.sh` 软链到 `~/.claude/templates/`，供 `/bootstrap` 与 `/sync-project-config` 在目标项目中铺设 / 同步。

| 模板                   | 适用项目                                                                     | 内容（节选）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_common/`             | 所有项目（其他 stack 自动叠加）                                              | 通用 issue templates（GitHub + GitLab 双轨）、`.github/labels.yml` 三轴 label、`.prettierrc` / `.prettierignore`（豁免 DEVTREE.md 免表格对齐）等                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `python-uv/`           | Python 项目（uv + ruff）                                                     | `.gitignore` / `.pre-commit-config.yaml` / `.vscode/` 配置片段（`extensions.json` + `settings.json` 的 `*.json.fragment`，合并进项目根 `.vscode/`：ruff 推荐 + `[python]`/`[markdown]` formatOnSave）/ `pyproject.toml` 四个片段（`[tool.ruff]` + `[tool.uv]` python-preference=only-managed + `[[tool.uv.index]]` 清华源 + `[tool.pytest.ini_options]` src 布局 pythonpath/testpaths） / `tests/` + `configs/` 骨架（与 src/ 平级）/ CI workflow（GitHub Actions `lint.yml` + GitLab CI `.gitlab-ci.yml`，后者为**变体组** `.variant.docker`/`.variant.shell`，bootstrap/sync 按 runner 类型选一个落地） |
| `python-uv-workspace/` | Python **多包单仓**（uv workspace），落工作区根、与单包 `python-uv` **互斥** | 虚拟根（`pyproject.toml` 无 `[project]`、仅 `[tool.uv.workspace] members=["packages/*"]`）+ 共享配置上提到根的 fragments（`[tool.uv]` only-managed / `[[tool.uv.index]]` 清华源 / `[tool.ruff]` 含 `extend-exclude` / `[tool.pytest.ini_options]` `--import-mode=importlib` + 列全各成员 `pythonpath`·`testpaths` / `.vscode/settings.json` `extraPaths`+`defaultInterpreterPath`）/ `packages/` 下两参考成员 `example_core`（库，纯逻辑可独立单测）+ `example_app`（应用，演示 `[tool.uv.sources] workspace=true` 跨成员依赖，各成员 `tests/` 无 `__init__.py`）/ `stack.yml`（`default_path: .`）       |
| `react-vite/`          | 前端项目（React + Vite），落 `frontend/` 子目录、与后端正交                  | `package.json`（React 19 + Vite 6 + TS strict，依赖版本写死）/ `.npmrc`（npmmirror）/ `biome.json`（前端的 ruff）/ `components.json`（shadcn new-york/neutral）/ `vite.config.ts`（`/api`·`/ws` proxy 范式）/ `tsconfig.json` / `index.html` / `src/` 基础件（`main.tsx` + `index.css` tailwind v4 CSS-first + theme-provider/mode-toggle 暗色可切 + shadcn Button + App 占位）/ `.vscode/` 配置片段（`extensions.json` + `settings.json` 的 `*.json.fragment`，合并进**项目根** `.vscode/`：Biome 推荐 + 语言作用域 formatOnSave）/ `stack.yml`（`default_path: frontend`）                              |
| `ros2/`                | ROS 2 项目（colcon 工作空间，可含多个 ROS 包），落工作空间根                 | 工作区级配置落 `__root__`（`.gitignore` colcon 产物 + `.ws/`/compile_commands 软链 / `ruff.toml` / `.clang-format` Google 100 列 / `.vscode/` 片段：ruff + clangd + cmake + ROS 扩展与语言作用域设置）/ `__subpath__/src/` 下两个参考包：`ros2_cpp_pkg`（ament_cmake，演示 ament-first CMake / 依赖消费导出 / install 路径 / 纯逻辑 + ROS 薄壳分层 + gtest）与 `ros2_py_pkg`（ament_python，纯逻辑 + 节点冒烟测）/ `stack.yml`（`default_path: .`）。Python 与 C++ 合一个 stack（一仓即一工作空间、可含多包，共享根配置）                                                                                 |

**平台双兼容**（round 14 引入，round 15 完成 skill 端双轨适配）：模板内容同时含 GitHub（`.github/...`）与 GitLab（`.gitlab/...` + `.gitlab-ci.yml`）两套等价文件，bootstrap / sync 一并落地——对端文件在另一平台等同于死文件，互不干扰。其中 `.gitlab-ci.yml` 是**变体组**（round 43 引入通用「变体组」机制）：模板存 `.variant.docker`（docker executor runner）/ `.variant.shell`（本地 shell runner，脚本装 uv、复用 `before_script` 用 YAML 锚点而非 `!reference`）两支，bootstrap/sync 初始化时按 runner 类型交互选一个落地为 `.gitlab-ci.yml`、选择记进 marker `stacks[].variants`——因为会被 GitLab 真实执行的配置不能多变体并存让用户手删。skill 中真正调命令行的步骤（如 labels 同步、issue 创建 / 查看）由 `scripts/platform_issue.py` 按 `git remote get-url origin` 自动 dispatch 到 `gh` / `glab`，SKILL.md 不直接调平台 CLI。`.github/labels.yml` schema 跨平台一致，GitLab 项目下也读同一份（不复制 `.gitlab/labels.yml`）。详见 [docs/11-跨项目共享模板与sync-skill/SCHEMA.md](docs/11-跨项目共享模板与sync-skill/SCHEMA.md) 末尾「关于平台双兼容」一节。

工作流：

- **新项目** → `/bootstrap` 选 stack（**可多选**，如后端 `python-uv` + 前端 `react-vite` 叠加），自动写入相关配置 + 生成 `.agent-template.yml` marker
- **已有老项目** → `/sync-project-config` 进入 adopt 模式补全 marker 并铺模板
- **模板更新后** → 在项目目录跑 `/sync-project-config` 拉新（AI 智能 merge，per-file 用户决策；normal sync 不重跑 stack bootstrap）

**python-uv stack 自动 bootstrap**（round 17 引入，round 25 改用 `uv init --package`）：`/bootstrap` 选 `python-uv` 与 `/sync-project-config` 走 adopt 路径时，除了落配置文件，还会自动跑 `uv init --package`（已有 `pyproject.toml` 时跳过）+ `uv add --dev pytest pytest-cov ruff` + 必要时 `uv tool install pre-commit` + `pre-commit install`。`--package` 让 uv 直接落标准 src 布局（`src/<pkg>/__init__.py` + 含 `[build-system] uv_build` 的 `pyproject.toml`）；模板配套 fragment 把 `[tool.pytest.ini_options] pythonpath=["src"] testpaths=["tests"]` 合并进 pyproject。新项目跑完 `/bootstrap` 立即可 `uv run pytest` / `git commit`，不需要再手敲命令。用户可选「只要配置不要装依赖」跳过整段。详见 [docs/17-python-uv模板自动bootstrap/SUMMARY.md](docs/17-python-uv模板自动bootstrap/SUMMARY.md) 与 [docs/25-python模板与子CLAUDE机制/SUMMARY.md](docs/25-python模板与子CLAUDE机制/SUMMARY.md)。

**python-uv-workspace stack 自动 bootstrap**（round 36 引入）：多包单仓（uv workspace）与单包 `python-uv` **互斥**、二选一。`/bootstrap` 选 `python-uv-workspace` 与 `/sync-project-config` 走 adopt 路径时，**不**跑 `uv init --package`（那会在虚拟根写出 `[project]` + `src/` 破坏 workspace 形态）——虚拟根 `pyproject.toml` 由本 stack 的 workspace fragments（`uv-workspace` / `uv` / `uv-index` / `ruff` / `pytest`）合并而成、成员包随模板 `packages/*` 复制就位，随后 `uv add --dev pytest pytest-cov ruff` 在虚拟根写 `[dependency-groups] dev` 并触发 `uv sync`（把各成员 editable 装入、解析跨成员 `workspace=true` 依赖）。跑完即可 `uv run pytest` 跑全树。布局细则见 [`playbooks/python.md` §2.2](playbooks/python.md)。

**react-vite stack 自动 bootstrap**（round 30 引入）：`/bootstrap` 选 `react-vite` 与 `/sync-project-config` 走 adopt 路径时，整套前端模板复制到 `frontend/` 子目录后，自动在 `frontend/` 跑 `npm install`（`.npmrc` 已固化 npmmirror 源，依赖走国内镜像）。前端 / 后端是正交两维、可同仓叠加（如 `python-uv` 落根 + `react-vite` 落 `frontend/`），marker 各记一条 `stack` + `path`。用户可选「只要文件不装依赖」跳过 `npm install`。详见 [docs/30-前端栈规则与scaffold模板/SUMMARY.md](docs/30-前端栈规则与scaffold模板/SUMMARY.md)。

## 多设备自动同步

每次换设备都手动 `git pull && bash install.sh` 很烦。本仓库把这件事交给 **OS 调度器**（[scripts/auto-update.sh](scripts/auto-update.sh)，30min 节流）：

| 触发方                                                    | 时机              | 输出                                                                            |
| --------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------- |
| **OS 调度器**（macOS launchd / Linux systemd user timer） | 登录跑 + 每小时跑 | 完整日志 → `$AGENT_HOME/logs/auto-update.log`（默认 `~/.claude/`），stdout 静默 |

> 曾另有一条 `SessionStart` hook 在每次会话启动时也跑一次同步。因为它绝大多数时候被同一个 30min 节流戳挡掉、什么都不做就退出，却仍要付出进程拉起 + `git fetch` 的启动延迟，已移除；同步全部由调度器承担。**未注册调度器的环境**（容器、云端 sandbox——`install.sh` 在无 dbus 容器里 systemd 注册本就会失败）因此没有自动同步，按其惯常做法在会话内显式 `git pull && bash install.sh` 即可。

**`bash install.sh` 末尾自动调 [scheduler/install.sh](scheduler/install.sh)** 注册 OS 调度器（macOS 写 `~/Library/LaunchAgents/com.claude-code-global.auto-update.plist` + `launchctl load -w`；Linux 写 `~/.config/systemd/user/` + `systemctl --user enable --now`）。失败 warn 不阻塞主 install。

> macOS 侧的注册**不是无条件 unload + load**：plist 内容未变且 job 已加载时直接跳过，正被该 job 承载时只更新 plist、把重注册推迟到下次登录。因为 `launchctl unload` 会杀掉该 job 名下**全部**进程 —— 而 `install.sh` 常常正是由这个 job 拉起的，就地重注册等于自杀。成败也不看 `launchctl load` 的退出码（它失败时照样返 0），改查 `launchctl list`。来龙去脉见 [docs/58-调度器自杀式重注册/SUMMARY.md](docs/58-调度器自杀式重注册/SUMMARY.md)。

**关键行为**：

- dirty working tree / non-fast-forward / 网络错误 → 跳过 + 写日志 + **不更新时间戳**（下次重试）
- `install.sh` 未成功跑完（被强杀或非零退出）→ 留下 `$AGENT_HOME/.auto-update-inflight` 标记，下次运行**告警并补跑**。没有它的话，此时 `git pull` 往往已成功，下次会走「已是最新」直接退出，部署就永久停在半截；标记里的时间戳是**最初**那次失败的时间，好看出「已经坏了多久」
- 只在 master 分支自动 pull
- 第一台设备首次仍要手动 `git clone + bash install.sh`（自举的硬限制）
- 正在跑的旧 Claude session 不会自动应用新配置，需 `/exit` 重开

**逃生舱**：取消调度器注册跑 `bash scheduler/uninstall.sh`。详细设计见 [docs/16-自动同步全局配置/SUMMARY.md](docs/16-自动同步全局配置/SUMMARY.md)。

## issue 的自动开发（云端 routine）

本仓积压的 issue 里有一大类**需求已写清、不需要讨论方案**——沉淀一条实战教训成 `playbooks/*.md` 的一节、加个小 skill、补条 template、修个边界清晰的 bug。这类活由 [claude.ai Routines](https://claude.ai) 每周一 / 三 / 五定时跑一条云端 Claude Code 会话自动做掉，人只在 PR 上做最后一道审批。

**两条通道，授权强度不同**：

| 通道 | 谁决定纳入 | 能改什么 |
| --- | --- | --- |
| 自动通道 | 模型分诊（保守判） | 只有文档落点 |
| **标记通道** | **owner 给 issue 打 `auto:take` label** | 放开到 `skills/`（除自己）/ `templates/` / `scripts/` / `hooks/` |

**为什么要第二条通道**：自动分诊判错的代价不对称、只能保守，于是一大批「其实完全够格」的 issue 被漏收。难度与风险自动区分不了，就让人来标——`auto:take` 的语义是「owner 已过目此条，背书其正文可被无人值守执行」。选 label 而非评论做闸是因为**公开仓任何人都能评论**，而 label 只有写权限者打得上，授权强度由 GitHub 权限模型保证。

**分诊结论会被缓存下来**（round 56）：被自动通道判掉的 issue 会长期留在 open 列表里，每周三次、每次重读一遍正文、每次得出同一个结论。故 routine 判掉一条就给它打上 `auto:skip`，下次在**不读正文**的那层硬过滤里直接跳过。**它不是 wontfix**——issue 仍 open、人照常可以做；而且 issue 一被编辑 / 评论 / 重开，[`auto-skip-reset.yml`](.github/workflows/auto-skip-reset.yml) 就自动摘掉这个 label，下次重新完整分诊。**为什么复活要靠 workflow 而不是存个时间戳**：三条存法都不通——存进 issue 评论要动 routine「绝不发评论」那道安全硬规则，读 timeline 的 labeled 事件云端取不到，存进仓库文件则 routine 常有零 PR 的运行、那次没有提交落点。于是干脆不存时刻，由 GitHub 在「有人动了」的那一刻直接摘标。

| 环节     | 做法                                                                                                                     |
| -------- | ------------------------------------------------------------------------------------------------------------------------ |
| 环境复现 | routine prompt 里 `git clone` + `bash install.sh`——skills / hooks 对当前会话**动态生效**，云端与本机跑同一套流程         |
| 逻辑落点 | **全在仓库**（[`skills/routine-dev/SKILL.md`](skills/routine-dev/SKILL.md)），claude.ai 上只留一句「读它并执行」的指针 |
| 平台交互 | 云端**没有 `gh`**、直连 `api.github.com` 被 403 → issue 与 PR 一律走**内置 GitHub MCP**；本机才走 `platform_issue.py`    |
| 合批     | 按**落点文件 + 主题**聚类，一批放几条**不设上限**（吞吐闸是 PR 数），单次 ≤ `--max-prs`（默认 5）个 PR                   |
| 汇报回路 | 云端**无编程可读的运行输出** → **PR 即唯一汇报出口**（含改动摘要、review 是否降级、本次跳过清单）                        |
| 审批     | PR 就是审批闸：手机收到推送 → review → 打 `ff-merge` label 或评论 `/ff` 合入                                             |

**边界**：自动通道只碰 `playbooks/*.md` / `GLOBAL_AGENTS.md` / `README.md` / `docs/`，**不碰任何可执行面**，`priority:P0` 留给人。标记通道解开落点限制与保守性排除（含 P0），但**四条红线绝不因 `auto:take` 放宽**：

- **`skills/routine-dev/**`（自己）** —— 这份 SKILL 定义的正是「什么可以被自动改」，允许自改 = 一次标记永久放宽此后所有运行的边界，而判断「有没有改语义」的正是它自己；
- **`agents/**`（自己的检查员）** —— `/review-loop` 编队的 `model` / `effort`，也就是它自己每个 commit 都要过的那道门禁的强度。与上一条同属一条权限提升链，只是隔了一层；
- **`install.sh`** —— 无单测，改坏了是**静默**的：所有设备的自动同步在下次 pull 后失败，失败发生在 OS 调度器里没人看着；
- **`.github/**`** —— 自动写 `master` 的那条路。

标记也**换不掉事实性判断**：正文没说清、现状已满足、撞了红线，照样跳过并在 PR 里点名。完整推导（含这条论证的已知弱点：owner 打 label 时未必逐字读过正文）见 [`skills/routine-dev/references/security-boundary.md`](skills/routine-dev/references/security-boundary.md) §7。选型与云端能力实测的来龙去脉见 `the-foundation` 仓 round 0。

### PR 批准即 fast-forward 合入

GitHub 原生的三种合并方式都拿不到真 FF——merge 留 merge commit，squash / rebase 会新造提交。而**把 PR head 直接推到默认分支时，GitHub 会自动把该 PR 标记为 merged**（官方称 indirect merge）。[`.github/workflows/ff-merge.yml`](.github/workflows/ff-merge.yml) 就建在这条性质上：

- **触发**：在 PR 上打 `ff-merge` label，或评论 `/ff`（两条路等价，评论取首行第一个词，故 `/ff 合并吧` 也认）；
- **动作**：先试纯 FF；默认分支在 review 期间前进了就先 rebase 再 FF，**冲突一律停手**（绝不 fallback 成普通 merge）；推送被拒会重取最新 base 重试至多 3 次；成功后关闭关联 issue、删分支、回一条带新旧 SHA 的回执评论。**任何一步失败都会在 PR 上留评论并摘掉 label**，不会出现「label 挂着、其实什么都没发生」；
- **关联 issue 由脚本显式关闭，不靠 GitHub**：indirect merge 恰好掉在 GitHub 两套自动关闭机制的缝里——commit message 的关键字只在「该提交**首次被推**、且推的就是默认分支」时生效（PR 分支已先推过一遍，于是只被记成 `referenced`），PR body 的关键字又要靠「PR 被合并」事件触发（indirect merge 只改 PR 状态、不走那条链路）。故 [`ff-merge.sh`](.github/scripts/ff-merge.sh) 从「本次合入的提交集合 + PR body」解析关闭关键字后自行 `gh issue close`。**这条对 `/routine-dev` 是必需品而非锦上添花**：它的幂等靠「排除已被 open PR 覆盖的 issue」，PR 合并后覆盖消失而 issue 还开着的话，下次运行就会把同一条原地重做；
- **安全**：本仓是公开仓、也是云端 agent 的信任根，故硬校验**发起人 == 仓库 owner**；两个事件都用「workflow 文件恒取自默认分支」的那一档（`pull_request_target` / `issue_comment`），PR 内容改不了将要合并它的这段逻辑；rebase 路径会把 PR 内容落进工作区，但该 job **全程不执行工作区里的任何文件**。

于是 `master` 上既没有 merge commit、也不会被改写 SHA，与 `/rebase`、`/finish` 的 worktree 收尾保持同一套 FF 直线历史纪律。

**唯一的硬边界**：**触及 `.github/workflows/` 的 PR 走不了这条路**——Actions 的 `GITHUB_TOKEN` 被 GitHub 服务端硬性禁止推送 workflow 文件，且 `permissions:` 块里没有可声明的对应 scope，提权也绕不过。这类 PR 会收到一条说明评论，请在本地 `git merge --ff-only` 后直推。`/routine-dev` 产出的 PR 天然不会命中（`.github/` 在它的禁止落点清单里）。

## 指令面的定期精简（云端 routine）

本仓所有文档与 skill 的迭代长期是**单向增长**——只加不减。实测指令面（`GLOBAL_AGENTS.md` + `skills/*/SKILL.md` + `playbooks/*.md`）总字符数：2026-04 是 32,495，2026-07 是 162,562，**四个月 4.8 倍，中间没有任何一次净减**。

round 52 对照 Anthropic《[The new rules of context engineering for Claude 5](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)》（其自述砍掉 Claude Code 系统提示 80%+ 而编码 eval 无可测量损失）逐条核到本仓，得到三条与直觉不同的结论：

1. **痛点不是常驻 token。** round 51 让 playbooks 退出常驻后，剩下的绝大部分是懒加载。真痛点是**单次加载密度**与**只增不减的棘轮**。
2. **最大头是「重复」不是「冗长」。** 同一套 review 判据曾写在 6 个地方；`sync-project-config` 里明写着「与 bootstrap Step 3.3.7 **同一份，改动时两处同步**」，`commit` 里明写着「细节以 `/review-loop` 为**单一真源**」——然后复述了 700 字符。
3. **本仓的文档密度是资产不是负债。** 每条规则背后都挂着一次真实事故的代价。LLM 精简器最容易干的事恰恰是把「为什么」删掉只留「是什么」，**盲目按字数精简会精准删掉最值钱的部分**。

于是 [`/routine-slim`](skills/routine-slim/SKILL.md) 的判据被钉成两张清单，且**先在 round 52 真刀真枪用过一遍**才固化成 routine（不是纸上推演）：

| | 内容 |
| --- | --- |
| **允许删除**（封闭清单） | ① 已有单一真源的重复表述（必须留指针）② 成组同向细则 → 上提为一句判断原则 ③ 事故 WHY 的**过程叙事** → 压成结论一句 ④ 失效引用 ⑤ Agent 已从工具 schema 得知的重复 |
| **禁止删除** | 事故 WHY 的**结论**（可压缩、不可消失）／安全禁令与硬边界／本仓特有的非标约定／**拿不准就保留** |

**只允许「搬走」不允许「蒸发」**——删除型 diff 的麻烦是「少了什么是看不见的」，`git diff` 告诉不了你那条信息是搬走了还是没了。两道护栏：PR 描述**强制三列表格**（删了什么 / 依据哪条判据 / 现在从哪读得到），以及 `context_budget.py check-refs` 机械校验所有指针可达（**指针指不到东西 = 那条信息真的没了**）。

| 维度 | 取值 |
| --- | --- |
| 触发 | 每周日 01:00 UTC（= 北京时间周日 09:00），且**增长 > 15% 才动手**，否则空转退出 |
| 逻辑落点 | **全在仓库**（[`skills/routine-slim/SKILL.md`](skills/routine-slim/SKILL.md)），claude.ai 上只留一句指针 |
| 出口 | PR 即审批闸（打 `ff-merge` label 或评论 `/ff` 即 FF 合入），同 `/routine-dev` |
| 一次做多少 | 1–3 个文件。删除型 diff 的 review 成本本就高，少而深胜过多而浅 |

**安全边界**（与 `/routine-dev` 的差异是有意的）：

- **可自动改** `skills/*/SKILL.md`、`skills/*/references/*.md`、`playbooks/*.md`；
- **只报告不动手** `GLOBAL_AGENTS.md` 与本仓 `CLAUDE.md`——宪法是所有 skill 的上位规则，一条能自动改它的 routine 就是能改自己上位约束的 routine；
- **永不碰** 自己、`/routine-dev`、`.github/`、`install.sh`、`scripts/`、`hooks/`、`templates/`、`docs/`。**不因为「只是精简、不改语义」而放宽——判断有没有改语义的正是它自己。**

**两条 routine 都能改 `skills/*.md`，但放宽的理由各是各的**：`/routine-dev` 把**外部 issue 正文**（任何人都能写）变成文件内容，是 prompt-injection 面，所以它的自动通道只许碰文档，越线要 owner **逐条**打 `auto:take` 背书；`/routine-slim` 只读仓库自身、不读任何外部文本，且只做删除与搬移、不引入新语义，故不需要逐条授权。**别互相援引。**

**两条 routine 的撞车防线（双向）**：`/routine-dev` 每周跑三次、也写 `playbooks/*.md`，自 round 54 起同样能改 `skills/*.md`，重叠面比原先更大；PR 又可能在人手上挂好几天——**光靠 cron 时间错开不够**。故**两边各守一道、不依赖对方**：`/routine-slim` 每次运行把所有 open PR 碰过的文件整体排除（列不出 open PR 就中止本次运行）；`/routine-dev` 开 PR 前的落点复核，其并集**初始值**同样是「所有 open PR 碰过的文件」——顺带也覆盖了人手开的 PR。

来龙去脉与量化见 [docs/52-指令面精简与定期化/](docs/52-指令面精简与定期化/)，其中 `SLIM-LEDGER.md` 是那一轮删减的完整三列账本。


## 开发项管理

详细规范见 [`GLOBAL_AGENTS.md`](https://github.com/pkulijing/claude-code-global/blob/master/GLOBAL_AGENTS.md) 中「核心开发模式 → 需求管理」段。要点：

- 开发项以 **issue 为单一真源**（GitHub / GitLab 自动双轨判定）：详情、讨论、跨轮上下文都沉淀在 issue，**无本地索引文件**
- open 项速览走一个按 priority label 过滤 open issues 的 **saved query**（本仓库：[open issues by priority](https://github.com/pkulijing/claude-code-global/issues?q=is%3Aissue+is%3Aopen+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2)），消除 BACKLOG.md 与云端 issue 的双写和 drift
- 三轴 label：`type:*`（feat/bug/refactor/perf/test/docs）、`area:*`（项目特异）、`priority:*`（P0/P1/P2）；**刻意决定不做**的项归档为带 `wontfix` 的 closed issue
- **`auto:take`（本仓特有，三轴之外）**：给一条 issue 打上，即声明「我已过目，背书其正文可被无人值守执行」——下次 `/routine-dev` 会**强制纳入**并解开落点限制（可改 `skills/` / `templates/` / `scripts/` / `hooks/`）。**难度与风险自动区分不了，就由人来标**；只有有写权限的人打得上，这正是选它而非评论做闸的原因。四条红线打了也解不开（见上文「issue 的自动开发」）
- **`auto:skip`（本仓特有，三轴之外，由 agent 自己打）**：与上一条相反——`/routine-dev` 判定「这条不适合无人值守做」时自己打上，下次运行**在读正文之前**就跳过它，省掉每次重新分诊的 token。**不是 wontfix**：issue 仍 open、人照常可以做；issue 一被编辑 / 评论 / 重开，[`auto-skip-reset.yml`](.github/workflows/auto-skip-reset.yml) 自动摘掉它。`auto:take` 永远压过它
- 工作流：`/backlog` 起新想法 → `/start <issue#>` 开新轮 → 执行中 Agent 自主 `/commit` 收口（每次 commit 前自动经 `/review-loop`：委派独立 context 子 agent 编队 review，默认 3 reviewer、复杂 diff 升 5 reviewer 含 opus 深审，迭代到「运行验证通过 + 无高置信 correctness 问题」）→ `/finish` 收尾时 PR/commit 写 `Closes #N` 自动关 issue（GitHub / GitLab 均原生支持）
