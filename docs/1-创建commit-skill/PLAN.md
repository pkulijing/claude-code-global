# 实现计划：创建 commit skill

## 方案

在 `skills/commit/` 下创建 `SKILL.md`，定义 commit skill 的行为规范，与现有 skill 格式保持一致。

## 涉及文件

- 新建：`skills/commit/SKILL.md`

## 验证

- 运行 `install.sh` 确认新 skill 被正确链接到 `~/.claude/skills/`
- 调用 `/commit` 验证 skill 可被识别
