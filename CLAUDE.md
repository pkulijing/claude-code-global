# claude-code-global

管理 Coding Agent 全局配置（`GLOBAL_AGENTS.md` + `skills/` + `hooks/` + `settings.base.json` + `codex.config.base.toml`）的仓库，通过 `install.sh` **双轨**部署到 `~/.claude/`（Claude Code）与 `~/.codex/`（OpenAI Codex）—— 单一真源，缺哪端就只装哪端。

## 目录结构

- `GLOBAL_AGENTS.md` — 全局开发规范（Development Constitution），通过 `install.sh` 链接为 `~/.claude/CLAUDE.md` 与 `~/.codex/AGENTS.md`，**修改此文件会影响所有项目、两端 agent**
- `settings.base.json` — CC 端 settings 基线（JSON），通过 `install.sh` **合并**（非覆盖）进 `~/.claude/settings.json`
- `codex.config.base.toml` — Codex 端 config 基线（TOML），通过 `install.sh` 以 marker 块形式**合并**进 `~/.codex/config.toml`
- `user.config.example.env` — 用户可配置项的示例基线（committed），`install.sh` 据此以 **user-wins**（缺省才填、绝不覆盖）语义 seed 出仓库外的真实配置 `~/.claude-code-global/config.env`；机制见 `docs/27-用户可配置项机制/DESIGN.md`
- `uv.config.base.toml` — 推荐的系统级 uv 配置基线（committed），`install.sh` 以 **user-wins** 语义 seed 到 `~/.config/uv/uv.toml`（缺失才创建，绝不覆盖）：默认 `python-preference = "only-managed"`（让 uv 全权管 python）+ 清华源默认 index
- `install.sh` — 安装脚本，双轨软链接 + 基线 settings/config 合并 + 用户可配置项 seed/应用 + 系统级 uv 配置 seed
- `skills/` — 全局 slash commands（`/start`、`/finish`、`/commit`、`/pybump`、`/rebase`、`/devtree` 等），双轨软链到两端 `skills/`
- `hooks/` — 全局 hook 脚本（如 `fix-after-edit.sh`），双轨软链到两端 `hooks/`，由各端 settings/config 中的 hook 条目以绝对路径引用
- `scripts/` — 被引用的稳定脚本，**逐文件**软链到两端 `scripts/`（新增 / 删除脚本需重跑 `install.sh`）。包括 `auto-update.sh`（多设备自动同步本仓库的 pull + install，由 OS 调度器触发，`AGENT_HOME` 变量化）、`user-config.sh`（用户可配置项的可 source 库：`ccg_seed_user_config` / `ccg_read_config` / `ccg_apply_git_default_branch`，供 install.sh 与未来 hook/skill 复用）、`context_budget.py`（指令面量化：`measure` / `delta --since` / `check-refs`，是 `/routine-slim` 的触发闸与「搬走而非蒸发」的机械兑现；token 估算系数由 `/context` 实测标定，**换模型后需重新标定**，单测在 `docs/52-指令面精简与定期化/test_context_budget.py`）
- `scheduler/` — OS 层调度器注册脚本与模板（macOS launchd / Linux systemd user timer），由 `install.sh` 末尾自动调用，注册"登录跑 + 每小时跑"的自动同步任务。逃生舱：`bash scheduler/uninstall.sh`
- `templates/` — 跨项目共享开发配置模板（`_common/` 全项目套用 + `<stack>/` 技术栈特异：后端 `python-uv`（单包）/ `python-uv-workspace`（多包单仓，与单包互斥）、前端 `react-vite`、ROS 2 工作空间 `ros2`），目录级软链到两端，由 `bootstrap` / `sync-project-config` 消费。各维正交、可同仓叠加。**落地机制（落点语义、fragment 合并、变体组、迁移去重）的单一真源是 `templates/MECHANICS.md`**，别在别处复述。两个非显然点：`ros2` 把 `ament_python` 与 `ament_cmake` 参考包合并在**单一** stack 内（一个仓库即一个 colcon 工作空间、可含多个 ROS 包，二者共享工作区根配置，拆两 stack 会在 `__root__` 撞车）；`.vscode/*.fragment` 一律汇聚到**项目根**（VS Code 单根工作区只读仓库根的 `.vscode/`）
- `playbooks/` — 领域规则文档（按 `<topic>.md` 拆分，如 `python.md`、`frontend.md`），目录级软链到两端 `playbooks/`，由 `GLOBAL_AGENTS.md` 顶层指针引用、Agent 命中触发条件时主动 Read。**曾用名 `rules/`，因撞上 CC 保留目录名而改名**（见下方「往 `~/.claude/` 下新增目录前先查保留名」）
- `.github/` — 本仓库自身的 GitHub 配置（**不部署到 agent 端**）：`labels.yml` 三轴 label + `ff-merge` 运维 label、`ISSUE_TEMPLATE/`，以及 `.github/workflows/ff-merge.yml` + `.github/scripts/ff-merge.sh`——在 PR 上打 `ff-merge` label 或评论 `/ff` 即把该 PR **fast-forward** 合入 `master`（GitHub 三种原生合并方式都拿不到真 FF；直推默认分支时 GitHub 会自动把 PR 标记为 merged）。校验发起人必须是仓库 owner，冲突一律停手不硬合。**改本 workflow 自身的 PR 用不了这条路**——`GITHUB_TOKEN` 被服务端禁止推送 `.github/workflows/` 下的文件，脚本会提前判掉并提示本地直推
- `docs/` — 开发记录，按轮次编号

## 开发注意事项

- 修改 `GLOBAL_AGENTS.md` 后无需重新安装（符号链接会自动生效）
- 新增或修改 `playbooks/*.md` 后无需重新安装（目录级软链，新加文件直接出现在 `~/.claude/playbooks/` 与 `~/.codex/playbooks/`）
- 修改 `templates/` 下文件内容后无需重新安装（同理目录级软链）；新增 stack 子目录或在 `__root__/` `__subpath__/` 加新条目，下游 `bootstrap` / `sync-project-config` 即时可见
- 新增或删除 skill 目录后需重新运行 `bash install.sh`
- 新增或删除 hook 脚本后需重新运行 `bash install.sh`（hook 脚本本体是软链，修改其内容无需重装）
- 修改 `settings.base.json` 或 `codex.config.base.toml` 后需重新运行 `bash install.sh`（合并的是快照，不是软链接）
- 修改 `user.config.example.env` 后需重新运行 `bash install.sh`（新增的 key 会「补缺追加」到用户真实配置，已设值不动）；用户真实配置 `~/.claude-code-global/config.env` 在仓库外，改完下次 install/自动同步即生效
- 修改 `uv.config.base.toml` 后需重新运行 `bash install.sh` 才会 seed（仅对 `~/.config/uv/uv.toml` **不存在**的机器生效，已有该文件的机器 user-wins 不覆盖）
- 修改 `.github/labels.yml` 后需跑 `python3 $HOME/.claude/scripts/platform_issue.py label-sync-from-file .github/labels.yml` 才会同步到 GitHub（不同步就打不了新 label）
- Codex 端 hooks 首次需进入 Codex 跑一次 `/hooks` 命令 review 后才生效
- **往 `~/.claude/` 下新增目录前，先确认该名字不是 CC 保留名。** 本仓踩过一次：`rules/` 是 CC 的**用户级 memory 目录**，软链过去等于把八份领域文档注册成「每会话全文常驻的系统提示」（约 19k token / 每会话），与「按需 Read」的设计意图正相反——详见 `docs/51-rules按需加载/`。已知保留名（CC 二进制里有 `join(configDir, X)` 构造）：`rules` / `skills` / `agents` / `commands` / `hooks` / `plugins` / `workflows` / `themes` / `plans` / `tasks` / `teams` / `projects` / `sessions` / `cache` / `backups` / `debug`。本仓的 `scripts/` / `templates/` / `playbooks/` 经核查均非保留名。核查方法：对 CC 二进制跑 `strings`，搜 `join(` 构造里出现的目录名
- 开发流程遵循 `GLOBAL_AGENTS.md` 中定义的四步模式（需求 - 计划 - 执行 - 总结）
- **本仓有两条云端定时 routine，它们的 SKILL.md 都是安全边界、别当普通文档改**：
  - `/routine-docs`（每天）把纯文档类 issue 做成 PR。它把**外部 issue 正文**变成文件内容，是 prompt-injection 面 —— 故禁止改 `skills/*.md` 与任何可执行面，完整攻击链见 `skills/routine-docs/references/security-boundary.md`
  - `/routine-slim`（每周日）按增长阈值把指令面精简一轮并出 PR。它**可以**改 `skills/*/SKILL.md` 与 `playbooks/*.md`（输入只有仓库自身、不读外部文本、只做删除与搬移），但**永不碰自己、`/routine-docs`、`.github/`、`install.sh`、`scripts/`、`hooks/`、`templates/`**，且对 `GLOBAL_AGENTS.md` 与本文件**只报告不动手**
  - 改 `.github/workflows/ff-merge.yml` 等于改自动写 `master` 的那条路。两条 routine 都**绝不以任何方式触发合入** —— `ff-merge` 的准入闸校验「发起人 == 仓库 owner」，而云端 routine 用的就是仓库主人的凭证，这道闸区分不了人和 agent
