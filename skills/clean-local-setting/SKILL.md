---
name: clean-local-setting
description: 清理当前项目 .claude/settings.local.json 中的 permissions 列表 —— 分类每条规则（删除/提升/重写/保留），交互确认后安全写回，全程保留备份
disable-model-invocation: true
---

用户调用此 skill 表示要整治当前项目的 `.claude/settings.local.json` —— 移除一次性调试残留、重写低效规则、去掉已被 base 覆盖的重复项，让 local 只保留真正的项目专属条目。

## 前置

- 工作目录（`pwd`）必须是某个项目根，存在 `.claude/settings.local.json`
- 参考基线：`~/.claude/claude-code-global/settings.base.json`（本仓库的软链源）。若该路径不存在，退而读 `~/.claude/settings.json`（安装合并后的产物）
- 规范文档：`~/.claude/claude-code-global/docs/8-权限配置治理与清理skill/REFERENCE.md`，规则分类的判断依据都来自这里

## 执行流程

### 阶段 1：读文件

1. 读取 `$(pwd)/.claude/settings.local.json`，若文件不存在直接报错退出
2. 读取基线 `settings.base.json`（按前置说明找路径）
3. 统计原始 allow / deny 条目数，后续报告要对比前后

### 阶段 2：分类

对 `permissions.allow` 每条规则打一个标签，四选一：

#### DELETE —— 一次性调试命令，不该进配置

判断特征（命中任一即可）：

- 含 `/tmp/` 或 `/private/tmp/` 路径
- 硬编码具体版本号：`v0.6.0a1`、`0.5.2`、`20260408` 这类
- 硬编码用户绝对路径 + 具体文件名（如 `xxd /Users/jing/Developer/foo/install.sh`）
- 长 `python3 -c "..."` 内联脚本（尤其含 `import json,sys; d=json.load(sys.stdin); ...` 模式）
- 一次性验证命令：`bash -n /abs/path`、`otool -L /abs/path`、`chmod +x /abs/path`、`unzip -l/-p dist/*.whl` 指向具体文件
- 临时测试 app 路径：`/tmp/TestXxx.app`、`clang -o /tmp/...`
- 硬编码的 curl 具体 URL（不是 `curl:*`）
- `mkdir -p /tmp/...`、`rm -rf /tmp/...`

#### PROMOTE —— 已被 base 覆盖

若规则的前缀已被 base 的某条规则覆盖（如 local 有 `Bash(git add:*)`、base 也有），建议从 local 移除，base 已经管够了。

注意宽 / 窄关系：

- base `Bash(uv:*)` 覆盖 local `Bash(uv run:*)`、`Bash(uv sync:*)`、`Bash(uv add *)` 等
- base `Bash(git -C:*)` 覆盖所有 `Bash(git -C /xxx/path <sub>)`
- base `Bash(grep:*)` 覆盖 local `Bash(grep -r '...' ...)`

#### REWRITE —— 低效写法，可归一化

典型模式：

- 写死引号的 git commit：`Bash(git commit -m ':*)`、`Bash(git commit -m ' *)` → 若 base 已有 `Bash(git commit:*)` 则标 PROMOTE；否则标 REWRITE 为 `Bash(git commit:*)`
- 写死绝对路径的 `git -C`：`Bash(git -C /abs/path status)` 等 → 若 base 有 `Bash(git -C:*)` 则 PROMOTE
- 中间带 `:` 的无效规则（如 `Bash(foo:* bar)`）→ REWRITE 成末尾 `:*` 或拆两条

#### KEEP —— 项目专属的合法条目

既不一次性、也不被 base 覆盖、写法也符合规范，保留。例如：

- `Bash(bash build.sh)` —— 项目专属脚本
- `Bash(bash /abs/path/项目内脚本.sh)` —— 虽含绝对路径但脚本本身持续使用
- `Read(//opt/homebrew/lib/**)` —— 项目依赖的系统路径
- `WebFetch(domain:xxx.com)` —— 项目相关的外部 API 域

当拿不准时：**倾向 KEEP**，不要替用户删。

### 阶段 3：输出 dry-run 报告

以 markdown 表格展示，按分类聚合：

```
### DELETE（建议删除，N 条）

| 原规则 | 理由 |
|---|---|
| `Bash(xxd /Users/jing/.../install.sh)` | 硬编码绝对路径+具体文件，一次性调试 |
| ... | ... |

### PROMOTE（已被 base 覆盖，建议删除，N 条）

| 原规则 | 被哪条 base 覆盖 |
|---|---|
| `Bash(git add:*)` | `Bash(git add:*)` |
| `Bash(uv run:*)` | `Bash(uv:*)` |

### REWRITE（建议重写，N 条）

| 原规则 | 建议改为 | 理由 |
|---|---|---|
| `Bash(git commit -m ':*)` | `Bash(git commit:*)` | 写死引号不匹配双引号调用 |

### KEEP（保留，N 条）

| 规则 |
|---|
| `Bash(bash build.sh)` |
| ... |
```

末尾给**前后条目数对比**：`allow: N → M`。

### 阶段 4：交互确认

向用户提供四种操作选项：

1. **全部 apply**：按建议全执行（DELETE/PROMOTE 删除，REWRITE 替换，KEEP 留着）
2. **跳过某几条**：用户指名"第 X 条留着" / "REWRITE 不改"
3. **手动编辑再 apply**：用户直接粘贴改好的 allow 列表
4. **取消**

**必须等用户显式确认后才进入阶段 5**。

### 阶段 5：备份 + 写回

1. `cp .claude/settings.local.json .claude/settings.local.json.bak.<YYYYMMDD-HHMMSS>`
2. 按确认后的列表构造新 JSON：
   - `allow` = KEEP 原条目 + REWRITE 新条目（去重）
   - `deny` 保持原样（本 skill 不动 deny，除非用户要求）
   - 其他字段（如 `permissions` 之外的 `env`、`hooks`）全部原样保留
3. 写回文件，格式化：2 空格缩进，键按 `allow` / `deny` 顺序

### 阶段 6：反馈

- 打印：`前: N 条 → 后: M 条（DELETE X / PROMOTE Y / REWRITE Z / KEEP W）`
- 打印备份文件路径
- 提醒用户可选：重跑 `~/.claude/claude-code-global/install.sh` 让全局 settings 重合并（如果他们觉得 base 也需要更新）

**不调用 `/commit`** —— 是否提交由人类决定。

## 注意

- **永远不改 base 和全局 settings**。本 skill 只动项目级 local。
- **不删 `permissions` 之外的字段**（`env`、`hooks`、`model` 等），即使项目自定义了也保留。
- **去重时用严格字符串等值**，不做语义去重（语义归并在分类阶段已完成）。
- 若 local 没有 `permissions.allow`，直接告知"本文件无需清理"并退出。
