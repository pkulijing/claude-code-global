# claude-code-global

管理 Coding Agent 全局配置（`GLOBAL_AGENTS.md` + `skills/` + `hooks/` + `settings.base.json` + `codex.config.base.toml`）的仓库，通过 `install.sh` **双轨**部署到 `~/.claude/`（Claude Code）与 `~/.codex/`（OpenAI Codex）—— 单一真源，缺哪端就只装哪端。

## 目录结构

- `GLOBAL_AGENTS.md` — 全局开发规范（Development Constitution），通过 `install.sh` 链接为 `~/.claude/CLAUDE.md` 与 `~/.codex/AGENTS.md`，**修改此文件会影响所有项目、两端 agent**
- `settings.base.json` — CC 端 settings 基线（JSON），通过 `install.sh` **合并**（非覆盖）进 `~/.claude/settings.json`
- `codex.config.base.toml` — Codex 端 config 基线（TOML），通过 `install.sh` 以 marker 块形式**合并**进 `~/.codex/config.toml`
- `install.sh` — 安装脚本，双轨软链接 + 基线 settings/config 合并
- `skills/` — 全局 slash commands（`/start`、`/finish`、`/commit`、`/pybump`、`/rebase`、`/devtree` 等），双轨软链到两端 `skills/`
- `hooks/` — 全局 hook 脚本（如 `fix-after-edit.sh`），双轨软链到两端 `hooks/`，由各端 settings/config 中的 hook 条目以绝对路径引用
- `scripts/` — 被引用的稳定脚本，双轨软链到两端 `scripts/`。包括 `auto-update.sh`（多设备自动同步本仓库的 pull + install，由 OS 调度器和 SessionStart hook 共用，`AGENT_HOME` 变量化）
- `scheduler/` — OS 层调度器注册脚本与模板（macOS launchd / Linux systemd user timer），由 `install.sh` 末尾自动调用，注册"登录跑 + 每小时跑"的自动同步任务。逃生舱：`bash scheduler/uninstall.sh`
- `docs/` — 开发记录，按轮次编号

## 开发注意事项

- 修改 `GLOBAL_AGENTS.md` 后无需重新安装（符号链接会自动生效）
- 新增或删除 skill 目录后需重新运行 `bash install.sh`
- 新增或删除 hook 脚本后需重新运行 `bash install.sh`（hook 脚本本体是软链，修改其内容无需重装）
- 修改 `settings.base.json` 或 `codex.config.base.toml` 后需重新运行 `bash install.sh`（合并的是快照，不是软链接）
- Codex 端 hooks 首次需进入 Codex 跑一次 `/hooks` 命令 review 后才生效
- 开发流程遵循 `GLOBAL_AGENTS.md` 中定义的四步模式（需求 - 计划 - 执行 - 总结）
