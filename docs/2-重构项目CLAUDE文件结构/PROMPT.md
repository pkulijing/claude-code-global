# 重构项目 CLAUDE.md 文件结构

## 背景

本项目（claude-code-global）的目标是作为系统级别的全局 CLAUDE.md 配置，通过 `install.sh` 符号链接到 `~/.claude/CLAUDE.md`，供所有项目共用。

当前的问题是：项目根目录的 `CLAUDE.md` 实际内容是全局开发规范（Development Constitution），而非描述本项目自身的说明文档。这导致：

1. 本项目缺少自己的 CLAUDE.md（项目性质介绍目前写在 README.md 里）
2. 在本项目中使用 Claude Code 时，读到的"项目级" CLAUDE.md 其实是全局规范，语义上有错位

## 需求

1. 将当前的 `CLAUDE.md`（全局开发规范）重命名为 `GLOBAL_CLAUDE.md`
2. 更新 `install.sh`，使符号链接指向新文件名 `GLOBAL_CLAUDE.md`
3. 重新创建符号链接 `~/.claude/CLAUDE.md` → `GLOBAL_CLAUDE.md`
4. 新建项目自身的 `CLAUDE.md`，描述本项目的性质、目录结构、开发与贡献方式
