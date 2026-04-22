# 需求：为全局仓库加入 settings.json 合并机制

## 背景

当前 `install.sh` 只做两件事：

- 把 `GLOBAL_CLAUDE.md` 软链接成 `~/.claude/CLAUDE.md`
- 把 `skills/*` 下的每个子目录软链接到 `~/.claude/skills/`

但使用时发现一个反复出现的体验问题：**每次调用全局 skill（`/commit`、`/rebase`、`/finish` 等）都会被权限弹窗打断**，需要手动点"允许"才能往下走。根据搜索结果，官方推荐的一劳永逸方案是在 `~/.claude/settings.json` 中加：

```json
{ "permissions": { "allow": ["Skill(*)"] } }
```

## 问题

`settings.json` 没法像 `CLAUDE.md` 那样直接软链接：

- 它里面既有**想在所有机器上生效**的共享设置（例如 `permissions.allow`）
- 又有**本机特有**的偏好（例如 `effortLevel: "high"`、可能的机器特定 `env`、个人快捷键等）
- 软链接会让本机没法再独立编辑它——一改就改了仓库

## 需求

给 `install.sh` 加一个**合并机制**：

1. 仓库里维护一份"基线 settings"（想在所有机器上都生效的最小集合）
2. `install.sh` 跑起来时把基线合并进 `~/.claude/settings.json`，而不是覆盖
3. 合并必须是**非破坏性**的：
   - 本地特有的键（`effortLevel` 等）原样保留
   - `permissions.allow` 这类数组要做**并集**，不能覆盖本地已加的权限
4. **幂等**：重复运行 `install.sh` 不应该反复产生备份文件或无意义改动
5. 首次需要写入的基线内容：`permissions.allow = ["Skill(*)"]`

未来如果有别的"想在所有机器上生效"的配置（例如更多权限白名单、hooks、环境变量），直接往基线文件里加就行。
