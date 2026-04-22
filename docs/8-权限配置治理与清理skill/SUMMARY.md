# 权限配置治理与清理 skill · 总结

## 开发项背景

**希望解决的问题**：

- `~/.claude/settings.json` 和各项目 `.claude/settings.local.json` 的 `permissions.allow` 长期累积成垃圾列表，混杂一次性调试命令、硬编码路径/版本、写法错误的规则
- 常用命令（`git commit -m "..."`、`git -C /some/path status`）反复弹窗，已有的授权条目并没有生效
- 缺乏对 CC 权限匹配规则的清晰心智模型，每次加授权都是"试出来"的

**本轮要同时产出的两件事**：

1. 基于调研的 `settings.base.json` 全局基线 + 可查询的写法小抄
2. 一个可复用的 `/clean-local-setting` skill，用它一次性清理已有 5 个项目

## 实现方案

### 关键设计

- **CC 的 Bash 权限规则是 glob 匹配，不是前缀匹配**。`Bash(git commit:*)` 等价于 `Bash(git commit *)`，末尾 `:*` 是语法糖。中间出现的 `:` 按字面量处理。
- **规则匹配的是命令原始字符串**，不是 shell-parse 后的 argv。这直接解释了旧配置里 `Bash(git commit -m ':*)` 为什么永远不命中 `git commit -m "任意"` —— 双引号字符串没有单引号，自然不匹配。
- **`:*` 形式在末尾**（其他位置无效），对齐官方示例写法。
- **跨仓库权限核弹**：`Bash(git -C:*)` 一条放行所有 `git -C /任意路径 任意子命令`，取代过去"每个仓库每个子命令写一条"的 N² 爆炸模式。
- **`additionalDirectories` 是另一条权限通道**：工具访问 CWD 外路径时先走工作区检查，再看 `permissions.allow` 里的 `Read(...)`。这意味着 `Read(//Users/jing/Developer/**)` 只对 Read 工具有效，管不住跨工作区的 Write/Bash。这是开发过程中通过实操发现的盲点。
- **安全边界在 deny**：通配 `allow` 阻不住参数变形攻击（官方原话），真正的安全靠 `deny` + 工具选择。

### 开发内容概括

**阶段 A · 规范沉淀**：

- `docs/8-*/REFERENCE.md` — CC 权限写法小抄，含匹配机制、优先级、常用命令推荐表、反例清单、来源链接
- 重写 `settings.base.json`：allow 46 条 + deny 7 条，覆盖高频只读 + 低风险写 + 跨仓库 git
- `install.sh` 合并机制验证通过

**阶段 B · skill 实现**：

- `skills/clean-local-setting/SKILL.md`
- 四分类模型：DELETE / PROMOTE / REWRITE / KEEP
- 强制 dry-run 报告 + 用户显式确认 + 备份 + 写回
- 通过 `install.sh` 自动软链接到 `~/.claude/skills/clean-local-setting`

**阶段 C · 清理 5 个项目**：

| 项目 | 前 | 后 | 净削减 |
|---|---|---|---|
| claude-code-global | 34 | 4 | -30 |
| novel-writing | 4 | 2 | -2 |
| MIT6.S978-Deep-Generative-Models | 3 | 0 | -3 |
| avatar-generator | 12 | 6 | -6 |
| whisper-input | 204 | 42 | -162 |
| **合计** | **257** | **54** | **-203（-79%）** |

每个项目清理前都有同目录备份 `settings.local.json.bak.<timestamp>`，可随时回滚。

### 额外产物

- 调研阶段使用 `claude-code-guide` 子 agent 拉取官方文档 + GitHub issues 原文（#24029 / #3428 / #10096），结论全部有出处
- `REFERENCE.md` 里附带"反例清单"，内容来自本仓库真实旧配置，未来新手查阅能直接对照自检

## 局限性

- **`/clean-local-setting` 的分类是启发式**，不是严格规则引擎。边缘 case（如"看起来像一次性但其实常用"）依赖 Claude 的判断，必须走用户交互确认。
- **`additionalDirectories` 没有写进 base**。原因：用户明确表示"只想允许一次性 Read，不要永久把开发根目录纳入工作区"。代价是跨项目写/执行每次仍会弹窗。
- **`deny` 清单保守**。目前只拦 `git push --force/-f`、`rm -rf /`、`.env` 读取。更多危险模式（如 `curl | bash`、`chmod 777`）未纳入。
- **Skill 假设基线路径**：`~/.claude/claude-code-global/settings.base.json`。如果未来仓库改名或未通过本 `install.sh` 部署，需要手动指定路径。

## 后续 TODO

- **扩充 deny 规则**：梳理社区常见"危险命令模板"清单，择优加入 base `deny`。
- **base 规则持续回灌**：随着更多项目清理，若发现某类条目在多个项目都 KEEP，应提升到 base。
- **skill 的 `additionalDirectories` 处理**：当前 skill 不动这个字段。如果用户以后想统一清理 `additionalDirectories` 里的残留，需要扩展 skill。
- **新项目的初始化模板**：是否要给 `start` skill 加一步"从模板生成空的 `.claude/settings.local.json`"，避免重复弹窗积累。
- **跨仓库实测验证**：在若干个真实项目日常使用 1-2 周，统计弹窗频次是否真的下降，再决定是否进一步收紧 allow / 扩充 deny。
