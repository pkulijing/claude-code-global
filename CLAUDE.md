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
- `scripts/` — 被引用的稳定脚本，双轨软链到两端 `scripts/`。包括 `auto-update.sh`（多设备自动同步本仓库的 pull + install，由 OS 调度器触发，`AGENT_HOME` 变量化）、`user-config.sh`（用户可配置项的可 source 库：`ccg_seed_user_config` / `ccg_read_config` / `ccg_apply_git_default_branch`，供 install.sh 与未来 hook/skill 复用）
- `scheduler/` — OS 层调度器注册脚本与模板（macOS launchd / Linux systemd user timer），由 `install.sh` 末尾自动调用，注册"登录跑 + 每小时跑"的自动同步任务。逃生舱：`bash scheduler/uninstall.sh`
- `templates/` — 跨项目共享开发配置模板（`_common/` 全项目套用 + `<stack>/` 技术栈特异，如后端 `python-uv`（单包）/ `python-uv-workspace`（多包单仓，与单包互斥）、前端 `react-vite`、ROS 2 工作空间 `ros2`），目录级软链到两端 `templates/`，由 `bootstrap` / `sync-project-config` skill 消费。各维正交、可同仓叠加；每个 stack 可放 `stack.yml` 自描述落点（`default_path`，缺省 `.`；`react-vite` 写 `frontend`，`ros2` 落根、参考包在 `__subpath__/src/`）。`ros2` 把 Python（`ament_python`）与 C++（`ament_cmake`）参考包合并在单一 stack 内（一个仓库即一个 colcon 工作空间、可含多个 ROS 包，二者共享工作区根配置，若拆两 stack 会在 `__root__` 撞车）。模板里 `*.fragment` 文件不直接落地、由 skill **合并**进目标：`pyproject.toml.<section>.fragment` → 根 `pyproject.toml` 对应段（TOML 段合并）；`.vscode/<name>.json.fragment` → 根 `.vscode/<name>.json`（JSON 合并）——后者让各 stack 的编辑器推荐 / 设置统一汇聚到**项目根** `.vscode/`，打开仓库根即生效。另一类 `<target>.variant.<key>` 文件是「一组互斥变体」（如 `.gitlab-ci.yml.variant.docker` / `.variant.shell` 按 GitLab runner 类型二选一），skill 在初始化时交互选一个、**只落选中那份**为 `<target>`，选择记进 marker `stacks[].variants`——因为 `.gitlab-ci.yml` 这类会被工具真实执行的配置不能多变体并存让用户删
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
- **本仓有一条云端定时 routine**（`/routine-docs`，逻辑见 `skills/routine-docs/SKILL.md`）会每天自动把纯文档类 issue 做成 PR。改动 `skills/routine-docs/SKILL.md` 等于改这条 routine 的行为；改 `.github/workflows/ff-merge.yml` 等于改自动写 `master` 的那条路——两者都是安全边界，别当普通文档改
