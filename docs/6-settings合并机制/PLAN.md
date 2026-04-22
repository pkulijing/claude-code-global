# 实现计划：为全局仓库加入 settings.json 合并机制

## 方案概览

1. **仓库里新增** `settings.base.json` —— 记录"想在所有机器上生效"的最小配置基线
2. **`install.sh` 新增一步**：把 `settings.base.json` **合并**进 `~/.claude/settings.json`（不软链接）
3. **合并用 `jq` 实现**（macOS 已自带 `/usr/bin/jq`），策略如下：
   - **object**：递归合并
   - **array**：并集去重（`unique`）—— 对 `permissions.allow` 这类数组至关重要
   - **scalar**：仓库胜出（基线即真源；本机不希望共享的标量就别放进 `settings.base.json`）
   - `null` 视为"未设置"，保留另一侧

这样 `effortLevel: "high"` 这种只存在于本地的键会原样保留；`permissions.allow` 会把 `"Skill(*)"` 追加进去而不是覆盖。幂等——多次运行结果不变。

## 具体改动

### 新建文件

**`settings.base.json`**（仓库根目录）：

```json
{
  "permissions": {
    "allow": ["Skill(*)"]
  }
}
```

起步内容只放 `Skill(*)`。今后要加其他全局基线配置，直接在这里追加即可。

### 修改 `install.sh`

新增函数 `merge_settings`，在链接 `GLOBAL_CLAUDE.md` 和 `skills/` 之后调用一次：

- **本地没有 settings.json**：直接复制基线文件过去（不是软链接，本机要自己编辑）
- **已经包含基线**：通过预先合并 + 和当前文件做字节级 diff，判断"没有变化"就跳过，不产生备份
- **需要合并**：先复制一份带时间戳的 `.bak`，再把合并结果写回

合并逻辑用 `jq -s` 读入两个 JSON（当前本地 + 基线），用递归函数处理：

```
merge(a; b):
  object ⨯ object → reduce 两边 key 的并集，对每个 key 递归 merge
  array  ⨯ array  → (a + b) | unique
  b == null       → a
  otherwise       → b  (仓库胜出)
```

前置检查：如果 `jq` 不存在，`exit 1` 并提示装一下（macOS 自带；Linux 各大包管理器都有）。

### 更新 `README.md`

在"工作原理"节补一张小表，说明两种部署方式：

| 文件 | 部署方式 |
|---|---|
| `GLOBAL_CLAUDE.md` / `skills/*` | 软链接到 `~/.claude/` |
| `settings.base.json` | 合并（深度合并 + 数组并集）到 `~/.claude/settings.json`，本机特有设置保留 |

并在 Skills 章节说明"为什么加 `Skill(*)`"。

### 更新 `CLAUDE.md`（项目级）

目录结构里加一行 `settings.base.json`。

## 涉及文件

- 新建：`settings.base.json`
- 新建：`docs/6-settings合并机制/PROMPT.md`（已存在本文档）
- 新建：`docs/6-settings合并机制/PLAN.md`（本文件）
- 修改：`install.sh`（加 `merge_settings` 函数 + 调用 + 前置 `jq` 检查）
- 修改：`README.md`（工作原理 / Skills 小节）
- 修改：`CLAUDE.md`（目录结构）

## 验证

1. **初始安装场景**：临时挪走 `~/.claude/settings.json`，跑 `bash install.sh`，应被正确创建。
2. **已有设置的合并场景**：还原本机的 `settings.json`（含 `effortLevel: "high"`），跑 `bash install.sh`：
   - 合并后应同时包含 `effortLevel: "high"` 和 `permissions.allow: ["Skill(*)"]`
   - 应生成一个 `settings.json.bak.<ts>` 备份
3. **幂等验证**：再跑一次 `install.sh`，本机文件不应被修改、也不应产生新 `.bak`（走"已跳过"分支）。
4. **数组并集验证**：手动在 `~/.claude/settings.json` 里加一条 `"Bash(ls:*)"`，再跑 `install.sh`，`Skill(*)` 与 `Bash(ls:*)` 都应保留。
5. **实际效果**：新开对话调用 `/commit` 等全局 skill，确认不再弹权限。

## 开放问题

- 是否要支持"从仓库移除某项基线"后自动清理本地？**本期不做**——移除基线项由人类手动处理，避免工具过度聪明误删本地配置。
- 是否做 `jq` 的 Python 回退？**不做**，把依赖写在 README 里。
