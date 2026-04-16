# claude-code-global

管理 Claude Code 全局配置（`GLOBAL_CLAUDE.md` + `skills/`）的仓库，通过符号链接部署到 `~/.claude/`。

## 目录结构

- `GLOBAL_CLAUDE.md` — 全局开发规范（Development Constitution），通过 `install.sh` 链接为 `~/.claude/CLAUDE.md`，**修改此文件会影响所有项目**
- `install.sh` — 安装脚本，将配置文件符号链接到 `~/.claude/`
- `skills/` — 全局 slash commands（`/start`、`/finish`、`/commit`、`/pybump`）
- `docs/` — 开发记录，按轮次编号

## 开发注意事项

- 修改 `GLOBAL_CLAUDE.md` 后无需重新安装（符号链接会自动生效）
- 新增或删除 skill 目录后需重新运行 `bash install.sh`
- 开发流程遵循 `GLOBAL_CLAUDE.md` 中定义的四步模式（需求 - 计划 - 执行 - 总结）
