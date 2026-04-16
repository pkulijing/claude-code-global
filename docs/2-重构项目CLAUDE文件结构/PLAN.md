# 实施计划：重构项目 CLAUDE.md 文件结构

## Context

本项目 `claude-code-global` 的定位是系统级全局 CLAUDE.md 配置仓库，通过 `install.sh` 将内容符号链接到 `~/.claude/CLAUDE.md`。但当前项目根目录的 `CLAUDE.md` 存放的是全局开发规范内容，项目自身缺少描述性的 CLAUDE.md，导致在本项目中使用 Claude Code 时语义错位。

## 实施步骤

### 1. 重命名全局规范文件

- `git mv CLAUDE.md GLOBAL_CLAUDE.md`
- 文件内容不变

### 2. 更新 install.sh

修改 install.sh 第 59-64 行，将源文件名从 `CLAUDE.md` 改为 `GLOBAL_CLAUDE.md`：

```bash
# 链接 GLOBAL_CLAUDE.md → ~/.claude/CLAUDE.md
if [ -f "$REPO_DIR/GLOBAL_CLAUDE.md" ]; then
    link_item "$REPO_DIR/GLOBAL_CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
else
    warn "仓库中未找到 GLOBAL_CLAUDE.md，跳过"
fi
```

### 3. 重新执行 install.sh 更新符号链接

- 运行 `bash install.sh`，让 `~/.claude/CLAUDE.md` 指向新的 `GLOBAL_CLAUDE.md`

### 4. 创建项目自身的 CLAUDE.md

新建 `CLAUDE.md`，内容聚焦于本项目的开发说明：

- 项目性质说明（全局 Claude Code 配置管理仓库）
- 目录结构概览（`GLOBAL_CLAUDE.md`、`install.sh`、`skills/`、`docs/`）
- 关键说明：`GLOBAL_CLAUDE.md` 是全局规范源文件，修改后会影响所有项目
- 开发注意事项（修改 skill 后需重新 install、文档规范等）

### 5. 同步更新 README.md

README 中的「CLAUDE.md 内容概览」部分引用的文件名需同步更新为 `GLOBAL_CLAUDE.md`。

## 涉及文件

| 文件 | 操作 |
|------|------|
| `CLAUDE.md` | git mv → `GLOBAL_CLAUDE.md` |
| `install.sh` | 修改引用文件名 |
| `CLAUDE.md`（新） | 新建，项目自身说明 |
| `README.md` | 更新文件名引用 |

## 验证

1. `readlink ~/.claude/CLAUDE.md` 确认指向 `GLOBAL_CLAUDE.md`
2. `cat ~/.claude/CLAUDE.md` 确认内容是全局开发规范
3. 在本项目目录下，`CLAUDE.md` 是项目自身说明，`GLOBAL_CLAUDE.md` 是全局规范
