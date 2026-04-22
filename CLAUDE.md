# claude-code-global

管理 Claude Code 全局配置（`GLOBAL_CLAUDE.md` + `skills/` + `settings.base.json`）的仓库，通过 `install.sh` 部署到 `~/.claude/`（软链接 + settings 合并）。

## 目录结构

- `GLOBAL_CLAUDE.md` — 全局开发规范（Development Constitution），通过 `install.sh` 链接为 `~/.claude/CLAUDE.md`，**修改此文件会影响所有项目**
- `settings.base.json` — 全局 settings 基线，通过 `install.sh` **合并**（非覆盖）进 `~/.claude/settings.json`
- `install.sh` — 安装脚本，负责软链接 + 基线 settings 合并
- `skills/` — 全局 slash commands（`/start`、`/finish`、`/commit`、`/pybump`、`/rebase`、`/devtree`）
- `docs/` — 开发记录，按轮次编号

## 开发注意事项

- 修改 `GLOBAL_CLAUDE.md` 后无需重新安装（符号链接会自动生效）
- 新增或删除 skill 目录后需重新运行 `bash install.sh`
- 修改 `settings.base.json` 后需重新运行 `bash install.sh`（合并的是快照，不是软链接）
- 开发流程遵循 `GLOBAL_CLAUDE.md` 中定义的四步模式（需求 - 计划 - 执行 - 总结）
