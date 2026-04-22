# Claude Code 全局配置

通过 GitHub 仓库管理 Claude Code 的全局配置（`CLAUDE.md` 和 `skills/`），支持多设备同步。

## 工作原理

Claude Code 会读取 `~/.claude/` 下的全局配置。本仓库通过 `install.sh` 按两种方式部署：

| 仓库文件 | 部署到 | 方式 | 说明 |
|---|---|---|---|
| `GLOBAL_CLAUDE.md` | `~/.claude/CLAUDE.md` | 软链接 | 修改仓库即修改实际配置，`git pull` 即完成同步 |
| `skills/*/` | `~/.claude/skills/*/` | 软链接（逐个子目录） | 不影响 `~/.claude/skills/` 下不属于本仓库的 skill |
| `settings.base.json` | `~/.claude/settings.json` | **合并**（非破坏性） | 本机特有设置保留；仅追加/覆盖基线里声明的项 |

`settings.json` 之所以不软链接，是因为它通常既含跨机共享设置（如 `permissions.allow`），又含本机特有偏好（如 `effortLevel`）。合并规则：

- **object**：递归合并
- **array**：并集去重（如 `permissions.allow` 会把仓库基线里的条目追加进本地已有的列表，而不是覆盖）
- **scalar**：仓库基线胜出；不想跨机共享的标量就别写进 `settings.base.json`
- 多次运行 `install.sh` 幂等；真正发生变化时会先备份成 `settings.json.bak.<timestamp>`

合并依赖 `jq`（macOS 自带 `/usr/bin/jq`；Linux 各发行版用包管理器安装）。

## 安装

```bash
git clone <repo-url> ~/Developer/claude-code-global
bash ~/Developer/claude-code-global/install.sh
```

重复执行 `install.sh` 是安全的（幂等），不会影响 `~/.claude/skills/` 下不属于本仓库的 skill。

## GLOBAL_CLAUDE.md 内容概览

`GLOBAL_CLAUDE.md` 定义了所有项目通用的开发规范：

| 模块 | 内容 |
|------|------|
| **核心开发模式** | 需求 → 计划 → 执行 → 总结的四步协作流程，每个开发项在 `docs/` 下留档（PROMPT.md / PLAN.md / SUMMARY.md） |
| **git 规则** | 中文 semantic commit message，AI 提交须带 Co-authored-by，`.gitignore` 按目录拆分 |
| **环境变量管理** | `.env.local`（真实值，gitignore）+ `.env.example`（占位符，提交），禁止泄露密钥 |
| **Python 开发规则** | 使用 uv 管理依赖（禁止 pip install），ruff 格式化，清华 + sjtu 镜像源 |

## Skills

基线 `settings.base.json` 中预置了 `permissions.allow: ["Skill(*)"]`，让所有 slash command 默认放行，避免反复弹权限确认。

### `/start` — 开始一个新的开发项

创建文档目录，撰写 PROMPT.md，进入计划模式撰写 PLAN.md 并等待确认，确认后再开始写代码。

```
/start <需求描述>
```

### `/finish` — 完成当前开发项

撰写 SUMMARY.md 总结文档，然后调用 `/commit` 提交所有变更。

```
/finish
```

### `/commit` — 提交代码

分析当前变更，自动生成中文 semantic commit message 并提交，末尾自动附加 Co-authored-by。

```
/commit
```
