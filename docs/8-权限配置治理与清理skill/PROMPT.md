# 权限配置治理与清理 skill

## 背景

当前 `~/.claude/settings.json` 和各项目 `.claude/settings.local.json` 的 `permissions.allow` 列表非常混乱。典型表现：

- **重复授权**：同一类命令存在多条等价但写法不同的条目（例如 `Bash(git commit -m ':*)` 和 `Bash(git commit -m ' *)` 同时存在）。
- **格式不统一**：有的用通配符 `:*`，有的用空格+`*`，有的把完整参数写死；规则匹配行为不一致。
- **反复弹窗**：像 `git commit -m "任意消息"` 这样的常用命令，在很多项目里仍被反复提示要求授权。
- **一次性残留**：whisper-input 项目累积了 ≈170 条规则，大量是一次性调试命令（`python3 -c "..."`、`/tmp/xxx`、硬编码版本号）。
- **跨仓库失效**：`Bash(git -C /Users/jing/Developer/claude-code-global status)` 这类写死路径 + 写死子命令的规则，换一个项目或操作就失效，必须重授权。

## 调研结论（已完成）

基于 [Claude Code 官方 permissions 文档](https://code.claude.com/docs/en/permissions.md) 和 GitHub issues #24029 / #3428 / #10096，得到以下要点（详见 `REFERENCE.md`）：

1. **匹配是 glob，不是前缀**。`*` 可跨空格、跨 `;|&&`。
2. **末尾 `:*` 与 ` *` 等价**，两者都是"该命令前缀 + 任意参数"；官方示例偏向 `:*`。
3. **中间的 `:` 按字面量处理**，不是通配。`Bash(git:* push)` 永远匹配不上。
4. **末尾不带 `*` 的规则是精确等值匹配**。
5. **CC 匹配的是命令原始字符串**（glob 形式）。所以 `Bash(git commit -m ':*)` 只能命中"真的用单引号"的命令；用户日常 `git commit -m "..."` 是双引号，永远不命中 —— 这正是"反复弹窗"的根因。
6. **优先级**：deny > ask > allow，首个命中规则生效。settings 合并顺序：enterprise > local > project shared > user。
7. **Bash 权限不是安全边界**：参数变形容易绕过，真正的安全靠 `deny` 规则。

## 目标

本轮产出两件事，一次性把权限治理从"土法试错"变成"有规范、有工具":

### 交付物 1：`settings.base.json` 权限模板

按调研结论重写仓库根的 `settings.base.json`，定义全局基线的 `allow` 与 `deny`。要求：

- 规则统一使用 `:*` 末尾形式（对齐官方示例）
- 覆盖高频只读命令（`git status/diff/log`、`ls/cat/grep/rg/find`）和低风险写操作（`git add/commit/mv`、`uv *`、`npm run *`）
- **`Bash(git -C:*)` 一条解决所有跨仓库操作**
- `git push` 不全放行（跨机器副作用），保留弹窗
- `deny` 覆盖常见危险操作（`git push --force*`、`rm -rf ~/*` 等）
- 通过 `install.sh` 合并到 `~/.claude/settings.json` 后生效

### 交付物 2：`/clean-local-setting` skill

用来清理任意项目的 `.claude/settings.local.json`。定位是**未来日常工具**——接手别人项目或回到自己长期未清的项目时，一键整治。

核心能力：

- 读取当前目录的 `.claude/settings.local.json`
- 对每条规则按分类规则打标签：
  - **DELETE**：一次性调试命令（含 `/tmp/`、硬编码版本号、硬编码临时路径、一次性 `python3 -c "..."`、`xxd /abs/path/specific_file` 等）
  - **PROMOTE**：已被 `settings.base.json` 覆盖的条目（本地重复无意义）
  - **REWRITE**：低效写法（写死引号、路径，可归一化成 `:*` 形式）
  - **KEEP**：项目专属的合法条目
- 输出一份 dry-run 报告给用户 review
- 交互式逐条确认（或一键 apply 整批）
- 清理前备份原文件

**验收**：用该 skill 清理以下 5 个项目的 `settings.local.json`，作为 skill 的首次跑通验证：

1. `claude-code-global`（34 条，中等脏）
2. `whisper-input`（≈170 条，最脏）
3. `avatar-generator`（12 条，较干净但有可提升项）
4. `novel-writing`（4 条）
5. `MIT6.S978-Deep-Generative-Models`（3 条）

清理后重跑 `install.sh`，日常操作弹窗应显著减少。

## 约束

- 全部文档中文
- 遵循四步开发模式（需求 / 计划 / 执行 / 总结）
- Skill 放到 `skills/clean-local-setting/`，通过 `install.sh` 软链接到 `~/.claude/skills/`
- 任何项目级 `settings.local.json` 的清理**必须先备份**再改
- 不要在本轮把 `settings.base.json` 写得过宽以至于误放行危险命令；宁可保守，让 `/clean-local-setting` 的"REWRITE 建议"去补

## 非目标

- 不处理 `settings.json` 的其他字段（hooks、env、model 等），本轮只治 `permissions`
- 不做自动化"清理所有项目"的批处理脚本，skill 是单项目交互式工具
- 不覆盖企业级 managed settings（我们不使用）
