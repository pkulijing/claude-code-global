# BACKLOG

待启动的开发项登记簿。每项包含背景、目标、备注；启动时搬到 `docs/N-xxx/PROMPT.md` 并从本表移除。

---

## 系统整理 Claude Code Permission 配置

### 背景

当前 `~/.claude/settings.json` 以及各项目 `.claude/settings.local.json` 的 `permissions.allow` 列表非常混乱，典型问题：

- **重复授权**：同一类命令存在多条等价但写法不同的条目（例如 `Bash(git commit -m ':*)` 和 `Bash(git commit -m ' *)` 同时存在）。
- **格式不统一**：有的用通配符 `:*`，有的用空格+`*`，有的把完整参数写死；规则匹配行为不一致。
- **反复弹窗**：像 `git commit -m "..."` 这样的常用命令，在很多项目里仍被反复提示要求授权，说明已有的授权条目并没有生效覆盖。
- **无清晰心智模型**：我自己并不清楚 CC 的权限匹配规则到底怎么工作，每次加权限都是"试出来"的。

### 目标

系统性研究 Claude Code 权限系统，产出一套可复用的规范与清理后的配置：

1. **搞清匹配规则**：CC `Bash(...)` 规则的精确匹配语义——前缀匹配？通配符如何解析？引号、转义、参数边界怎么处理？
2. **确定最佳实践**：针对常见命令类别（git 操作、包管理器、文件读写、项目内脚本）给出推荐的授权写法模板。
3. **清理现有配置**：
   - 合并/删除 `settings.local.json` 中的重复项
   - 把真正应该全局化的条目提升到 `~/.claude/settings.json` 或本仓库的 `settings.base.json`
   - 项目级只保留与项目相关的条目
4. **修好 git commit 弹窗问题**：找到一条能稳定命中 `git commit -m "任意消息"` 的规则写法，写进 `settings.base.json`。

### 备注

- 入口文件：`~/.claude/settings.json`、各项目 `.claude/settings.local.json`、本仓库 `settings.base.json`。
- 需要同时翻 Claude Code 官方文档关于 permissions / tool permission rules 的章节，以及实际抓几条弹窗时的原始命令字符串做样本对照。
- 清理后的规则要反向写进 `settings.base.json`，让 `install.sh` 的合并机制下发到所有项目。
