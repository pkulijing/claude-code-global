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
- `scripts/` — 被引用的稳定脚本，双轨软链到两端 `scripts/`。包括 `auto-update.sh`（多设备自动同步本仓库的 pull + install，由 OS 调度器和 SessionStart hook 共用，`AGENT_HOME` 变量化）、`user-config.sh`（用户可配置项的可 source 库：`ccg_seed_user_config` / `ccg_read_config` / `ccg_apply_git_default_branch`，供 install.sh 与未来 hook/skill 复用）
- `scheduler/` — OS 层调度器注册脚本与模板（macOS launchd / Linux systemd user timer），由 `install.sh` 末尾自动调用，注册"登录跑 + 每小时跑"的自动同步任务。逃生舱：`bash scheduler/uninstall.sh`
- `templates/` — 跨项目共享开发配置模板（`_common/` 全项目套用 + `<stack>/` 技术栈特异，如后端 `python-uv`、前端 `react-vite`），目录级软链到两端 `templates/`，由 `bootstrap` / `sync-project-config` skill 消费。前端 / 后端是正交两维、可同仓叠加；每个 stack 可放 `stack.yml` 自描述落点（`default_path`，缺省 `.`；`react-vite` 写 `frontend`）。模板里 `*.fragment` 文件不直接落地、由 skill **合并**进目标：`pyproject.toml.<section>.fragment` → 根 `pyproject.toml` 对应段（TOML 段合并）；`.vscode/<name>.json.fragment` → 根 `.vscode/<name>.json`（JSON 合并）——后者让各 stack 的编辑器推荐 / 设置统一汇聚到**项目根** `.vscode/`，打开仓库根即生效
- `rules/` — 领域规则文档（按 `<topic>.md` 拆分，如 `python.md`、`frontend.md`），目录级软链到两端 `rules/`，由 `GLOBAL_AGENTS.md` 顶层指针引用、Agent 命中触发条件时主动 Read
- `docs/` — 开发记录，按轮次编号

## 开发注意事项

- 修改 `GLOBAL_AGENTS.md` 后无需重新安装（符号链接会自动生效）
- 新增或修改 `rules/*.md` 后无需重新安装（目录级软链，新加文件直接出现在 `~/.claude/rules/` 与 `~/.codex/rules/`）
- 修改 `templates/` 下文件内容后无需重新安装（同理目录级软链）；新增 stack 子目录或在 `__root__/` `__subpath__/` 加新条目，下游 `bootstrap` / `sync-project-config` 即时可见
- 新增或删除 skill 目录后需重新运行 `bash install.sh`
- 新增或删除 hook 脚本后需重新运行 `bash install.sh`（hook 脚本本体是软链，修改其内容无需重装）
- 修改 `settings.base.json` 或 `codex.config.base.toml` 后需重新运行 `bash install.sh`（合并的是快照，不是软链接）
- 修改 `user.config.example.env` 后需重新运行 `bash install.sh`（新增的 key 会「补缺追加」到用户真实配置，已设值不动）；用户真实配置 `~/.claude-code-global/config.env` 在仓库外，改完下次 install/自动同步即生效
- 修改 `uv.config.base.toml` 后需重新运行 `bash install.sh` 才会 seed（仅对 `~/.config/uv/uv.toml` **不存在**的机器生效，已有该文件的机器 user-wins 不覆盖）
- Codex 端 hooks 首次需进入 Codex 跑一次 `/hooks` 命令 review 后才生效
- 开发流程遵循 `GLOBAL_AGENTS.md` 中定义的四步模式（需求 - 计划 - 执行 - 总结）
