# 总结：为全局仓库加入 settings.json 合并机制

## 背景

**希望解决的问题**：每次调用全局 skill（`/commit`、`/rebase`、`/finish` 等）都会被 Claude Code 的权限弹窗打断。官方推荐的方案是在 `~/.claude/settings.json` 里加 `permissions.allow: ["Skill(*)"]`。

**遇到的障碍**：原来的 `install.sh` 只会做软链接，但 `settings.json` 既含跨机共享设置（权限白名单）又含本机特有偏好（如 `effortLevel: "high"`），不能简单软链接覆盖——需要一个**非破坏性合并**机制。

## 实现方案

### 关键设计

1. **基线 + 合并**：仓库维护 `settings.base.json`（想在所有机器上生效的最小集合），`install.sh` 把它合并进本地 `~/.claude/settings.json`，而不是链接或覆盖。
2. **合并策略（用 `jq` 实现）**：
   - object → 递归合并
   - array → 并集去重（`unique`）—— 对 `permissions.allow` 这类数组至关重要
   - scalar → 仓库胜出（基线即真源；不想跨机共享的标量不要写进基线）
   - null → 保留另一侧
3. **幂等 + 最小扰动**：先算出合并结果，再用 `jq '.'` 规范化本地文件做字节比较，只有真的变了才写盘并生成时间戳备份。重复运行不产生多余 `.bak`。

### 开发内容概括

- 新增 `settings.base.json`（起步内容：`permissions.allow: ["Skill(*)"]`）
- 在 `install.sh` 中新增 `merge_settings` 函数与调用，含 jq 依赖检查、等价性检查、时间戳备份
- 更新 `README.md`（工作原理加一张部署方式对照表 + 解释 `Skill(*)` 的作用）
- 更新 `CLAUDE.md`（目录结构加入 `settings.base.json` 说明）

### 额外产物

- **踩坑注释**：jq 函数参数是"滤镜表达式"，在 `reduce` 内部 `.` 变为累加器后，`a[$k]` 会被解成"索引累加器"而报错 `Cannot index object with number`。修复办法是先 `a as $a | b as $b` 把两侧绑定为真值。这条坑已作为注释写进 `install.sh`，未来改合并逻辑时少踩一次。

## 局限性

1. **不支持"从仓库移除某项基线"后自动清理本地**：当前 `merge_settings` 只做并集/覆盖，不做减法。如果以后想从基线里撤掉某条权限，本地 `settings.json` 里那条需要手动删。刻意设计——避免工具过度聪明误删本机配置。
2. **`jq` 是硬依赖**：macOS 自带（`/usr/bin/jq`），大多数 Linux 发行版也容易装。没有 `jq` 时脚本会打一条 `[WARN]` 并跳过合并，不会中断安装。没做 Python 回退，未来如果在不装 `jq` 的环境上用再考虑。
3. **`permissions.allow` 数组会被 jq `unique` 排序**：首次合并写回时顺序可能变（比如把本地已有的 `Bash(ls:*)` 排到 `Skill(*)` 前面）。功能上等价，但一次额外的"形变"会触发一次备份。之后再跑就真的 no-op。

## 后续 TODO

- 如果后续发现还有其他"每台机器都想要"的全局 Claude Code 配置（例如其他 `permissions.allow`、hooks、常用 env），直接追加到 `settings.base.json` 即可，合并逻辑无需改动。
- 观察一段时间 `Skill(*)` 是否足够；如果仍有某些工具触发弹窗（例如特定 Bash 命令），评估是否把更精细的白名单条目也纳入基线。
