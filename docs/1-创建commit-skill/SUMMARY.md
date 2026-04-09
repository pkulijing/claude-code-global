# 开发总结：创建 commit skill

## 开发项背景

`finish` skill 中引用了 `/commit`，但该 skill 尚未创建，导致 `/finish` 流程无法完整执行。

## 实现方案

### 关键设计

创建 `skills/commit/SKILL.md`，定义了标准的提交流程：查看变更 → 分析内容 → 生成中文 semantic commit message → 暂存 → 提交（含 Co-authored-by）→ 确认。

### 开发内容概括

- 新建 `skills/commit/SKILL.md`
- 运行 `install.sh` 将新 skill 链接到 `~/.claude/skills/`

### 额外产物

- `docs/1-创建commit-skill/` 下的 PROMPT.md、PLAN.md

## 局限性

- commit skill 目前不支持参数（如指定 commit message 或 scope）

## 后续 TODO

- 可考虑支持传入参数覆盖自动生成的 commit message
