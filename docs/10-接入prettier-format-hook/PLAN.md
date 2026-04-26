# PLAN — 接入 prettier/ruff format-after-edit hook

## 整体思路

仓库新增 `hooks/` 目录存放 hook 脚本，`install.sh` 仿照 `skills/` 的逐文件软链方式部署到 `~/.claude/hooks/`，`settings.base.json` 中 hook command 用 `$HOME/.claude/hooks/format-after-edit.sh` 绝对路径（避免依赖 cwd）。

## 改动清单

### 1. 新建 `hooks/format-after-edit.sh`

1:1 复制 daobidao 的脚本：

```bash
#!/usr/bin/env bash
# PostToolUse hook: auto-format file edited by Claude Code.
# Dispatches by extension: .py -> ruff format, .md -> prettier.
# Best-effort: never blocks the agent on formatter failure.

set -u

FILE=$(jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[ -z "$FILE" ] && exit 0
[ -f "$FILE" ] || exit 0

case "$FILE" in
  *.py)
    uv run --quiet ruff format "$FILE" >/dev/null 2>&1
    ;;
  *.md)
    command -v prettier >/dev/null 2>&1 \
      && prettier --write --log-level warn "$FILE" >/dev/null 2>&1
    ;;
esac

exit 0
```

`chmod +x` 保留可执行位。

### 2. `settings.base.json` 增加 PostToolUse hook

合并进现有结构（`merge_settings` 的 array 并集去重 + object 递归合并会负责正确合并）：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $HOME/.claude/hooks/format-after-edit.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

`$HOME` 由 shell 展开（CC hook command 走 shell）。

### 3. `install.sh` 增加 hooks 软链

仿照 skills 那段（line 124-133）：

- `mkdir -p "$TARGET_DIR/hooks"`
- 遍历 `$REPO_DIR/hooks/*` 逐文件 `link_item`
- 放在 skills 段之后、settings 合并之前

### 4. `GLOBAL_CLAUDE.md` 增加项目本地推荐配置约定

在合适位置（考虑放在「Python 开发规则」之后或独立小节）增加：

```markdown
## 项目本地推荐配置

以下配置不在全局仓库维护（受项目根目录约束），但建议每个项目都加：

- `.prettierrc`：`{ "proseWrap": "preserve" }`，防止 prettier 强制换行中文长段落
- `.vscode/settings.json`：`[markdown]` / `[python]` 块设置 `formatOnSave + defaultFormatter`，与全局 hook 输出对齐
- `.vscode/extensions.json`：推荐 `esbenp.prettier-vscode` / `charliermarsh.ruff`
```

### 5. `CLAUDE.md`（项目）更新目录结构

在「目录结构」段加入 `hooks/` 一行，「开发注意事项」加一条「新增/修改 hook 后需重新运行 `bash install.sh`」。

### 6. 文档：`docs/DEVTREE.md` + `docs/BACKLOG.md`

- DEVTREE：新增 round 10 节点（按现有 epic 结构归类，可能挂在「skill 与硬件能力」epic 下，或新建「钩子与自动化」epic —— 由 `/devtree` skill 在执行后处理）
- BACKLOG：本次没有遗留新条目，不动

## 测试计划

执行后逐项验证：

1. `bash install.sh` 输出包含 "已链接 format-after-edit.sh"，无报错
2. `ls -la ~/.claude/hooks/` 显示软链指向仓库
3. `jq '.hooks.PostToolUse' ~/.claude/settings.json` 输出包含新增的 matcher entry
4. 在本仓库编辑某个 `.md` 文件触发 hook（如果本机装了 prettier），文件被格式化
5. 在某个不含 prettier 的环境编辑 `.md`，hook 静默退出，不阻塞 agent
6. daobidao 删除项目本地 hook 后，全局 hook 仍触发（用户自测）

## 待确认问题

1. **路径展开**：CC 文档没明说 hook command 是否经过 shell。如果 `$HOME` 不展开，要改成硬编码 `/home/jing/.claude/hooks/...` 或在脚本里包一层。**默认认为走 shell 会展开**，跑一次就知道。
2. **健壮性优化（不在本轮做）**：当前 `uv run --quiet ruff format` 在非 uv 项目会失败但被静默吞掉。后续可以加「先试 `command -v ruff` → fallback `uv run`」，作为一个 backlog 条目跟进。本轮 1:1 移植。
3. **DEVTREE epic 归属**：本轮属于「自动化/IDE 协同」类，DEVTREE 上没有完全对应的 epic。是否新建一个，留给 `/devtree` skill 执行时由用户决定。
