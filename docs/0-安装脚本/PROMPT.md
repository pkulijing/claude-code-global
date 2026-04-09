# 需求：安装脚本

## 背景

用户有多台开发设备，希望通过 GitHub 仓库同步 Claude Code 的全局配置（`CLAUDE.md` 和 `skills/`）。仓库已建立，包含 `CLAUDE.md` 和 `skills/` 目录。

## 需求

编写一个安装脚本（`install.sh`），将仓库中的配置文件通过符号链接部署到 `~/.claude/` 目录下：

1. **CLAUDE.md**：将仓库中的 `CLAUDE.md` 软链接到 `~/.claude/CLAUDE.md`
2. **skills/**：遍历仓库中 `skills/` 下的每个子目录，逐个软链接到 `~/.claude/skills/` 下（而非整个 `skills/` 目录做单一软链接），以保留用户在其他来源添加的 skills

## 约束

- 不能影响 `~/.claude/` 下的其他文件（如 `settings.json`、`projects/` 等）
- 不能删除 `~/.claude/skills/` 下不属于本仓库的 skill
- 需要处理已存在文件/链接的情况（如重复执行脚本时的幂等性）
