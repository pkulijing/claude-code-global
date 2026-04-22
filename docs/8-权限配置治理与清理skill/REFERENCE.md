# Claude Code 权限写法小抄

本文档沉淀第 8 轮开发中对 CC 权限规则匹配语义的调研结论，供以后写 `permissions.allow` / `deny` 时直接查，不用再上网。

## 1. 匹配机制

### 1.1 基本形式

`permissions.allow` / `deny` 列表里，每条规则形如：

```
ToolName(pattern)
```

`ToolName` 可以是 `Bash`、`Read`、`Edit`、`Write`、`Skill`、`WebFetch`、`WebSearch` 等。本文档重点讲 `Bash(...)`。

### 1.2 Bash 规则是 **glob 匹配**（不是前缀匹配）

| 规则 | 匹配什么 |
|---|---|
| `Bash(git status)` | **精确等值**：只匹配命令字符串等于 `git status` 的调用 |
| `Bash(git status *)` | `git status` 开头 + **任意后缀**（包括空） |
| `Bash(git status:*)` | **等价于** `Bash(git status *)`，`:*` 是 " 加 `*`"的糖 |
| `Bash(git:* push)` | **永远不匹配**。中间的 `:` 被当字面字符，不是通配符 |
| `Bash(git * main)` | 匹配 `git <任意> main`，例如 `git merge main`、`git rebase origin main` |

核心三条规律：

1. **`*` 是通配符**，可跨空格、跨 `;` `|` `&&` `||` 等 shell 操作符。
2. **`:*` 仅在规则末尾是语法糖**，等价于空格 + `*`。中间出现的 `:` 被当字面字符。
3. **末尾不带 `*` 就是精确等值**，不是前缀。

### 1.3 Compound command 自动拆分

当用户同意 `git status && npm test` 并点"Yes, don't ask again"时，CC 会保存**两条独立规则** `Bash(git status)` 和 `Bash(npm test)`，而不是保留 `&&`。所以你在 settings 里也不用自己写 `&&`。

### 1.4 规则作用于"命令字符串"而非 argv

这是一个**容易踩坑的关键点**。CC 把用户执行的 bash 命令作为**原始字符串**去和规则 glob 匹配，不是先 shell-parse 成 argv 再匹配。

所以：

- 用户执行 `git commit -m "feat: 新功能"` → 字符串里有**双引号**
- 用户执行 `git commit -m 'feat: 新功能'` → 字符串里有**单引号**
- 规则 `Bash(git commit -m ':*)` 只会匹配后者；写了 `-m '` 字符的规则永远对双引号命令失效。

**正确做法**：不要在规则里写引号。用 `Bash(git commit:*)` 一条覆盖所有 `git commit` 开头的调用。

## 2. 优先级

### 2.1 规则评估顺序

```
deny  >  ask  >  allow
```

首个命中的规则生效。所以：

- 想"默认允许但禁止某种特定形式"，用 `deny` 里精确写出危险形式，`allow` 用宽松通配。
- `allow` 里再宽，只要 `deny` 命中就被拦。

### 2.2 Settings 文件合并顺序（从高到低优先级）

1. Enterprise managed settings（企业级，不使用就忽略）
2. 命令行参数 `--permission-mode` 等
3. **项目** `.claude/settings.local.json`（gitignore，个人本地）
4. **项目** `.claude/settings.json`（随仓库 check-in，团队共享）
5. **用户** `~/.claude/settings.json`（全局）

`allow` / `deny` 列表是**数组合并（并集）**，不是覆盖。所以 base 里写进的条目，即使 local 没写也生效。

## 3. 推荐写法速查表

### 3.1 Git

| 场景 | 推荐规则 | 备注 |
|---|---|---|
| `git commit -m "任意消息"` | `Bash(git commit:*)` | 一条覆盖 `-m`、`--amend`、`-a` 等所有变体 |
| `git -C /任意路径 <任意子命令>` | `Bash(git -C:*)` | **跨仓库操作的关键规则**，一条放行 |
| 只读查询 | `Bash(git status:*)`、`Bash(git diff:*)`、`Bash(git log:*)`、`Bash(git show:*)`、`Bash(git branch:*)`、`Bash(git blame:*)` | 分开写便于 deny 覆盖 |
| 低风险写 | `Bash(git add:*)`、`Bash(git mv:*)`、`Bash(git rm:*)`、`Bash(git reset:*)`、`Bash(git checkout:*)`、`Bash(git stash:*)` | 操作本地工作区 |
| 分支/标签 | `Bash(git branch:*)`、`Bash(git tag:*)`、`Bash(git fetch:*)`、`Bash(git merge:*)`、`Bash(git rebase:*)` | |
| **`git push` 整条** | **不放行**。保留弹窗 | 跨机器副作用，每次确认更稳 |
| `git push --force` | `deny` 明确禁 | 强制推送危险 |

### 3.2 包管理器

| 工具 | 推荐规则 |
|---|---|
| uv | `Bash(uv:*)` |
| npm 脚本 | `Bash(npm run:*)`（注意不是 `npm:*`，install/publish 不放行更稳） |
| pnpm | `Bash(pnpm:*)` |
| bun | `Bash(bun:*)` |

### 3.3 只读探查

```
Bash(ls:*)    Bash(cat:*)    Bash(wc:*)
Bash(find:*)  Bash(grep:*)   Bash(rg:*)
Bash(jq:*)    Bash(file:*)   Bash(which:*)
Bash(head:*)  Bash(tail:*)
```

### 3.4 文件访问（Read / Edit / Write）

| 场景 | 写法 |
|---|---|
| 放行某目录下所有文件 | `Read(/path/**)` |
| 禁敏感文件 | `deny: Read(./.env)`、`Read(./.env.local)` |

## 4. 反例清单（本仓库旧配置里真实出现过）

| 错误规则 | 为什么错 | 正确写法 |
|---|---|---|
| `Bash(git commit -m ':*)` | 只匹配真的用单引号的命令；双引号命令永远命中不了 | `Bash(git commit:*)` |
| `Bash(git commit -m ' *)` | 同上，把引号字符写进规则 | `Bash(git commit:*)` |
| `Bash(git -C /Users/jing/Developer/foo status)` | 路径 + 子命令都写死，换个项目/换个子命令就失效 | `Bash(git -C:*)` |
| `Bash(xxd /Users/jing/Developer/claude-code-global/install.sh)` | 一次性调试命令，硬编码路径 | 不该进配置，会话内 "Yes once" |
| `Bash(unzip -l /...whisper_input-0.5.2-py3-...whl)` | 硬编码版本号，一次性 | 不该进配置 |
| `Bash(python3 -c "import json,sys; d=json.load(sys.stdin); ...")` | 一次性脚本 | 不该进配置 |
| `Bash(jq '.permissions.allow = [\"Skill\\(*\\)\"]' ...)` | 一次性 jq 调用 | 不该进配置 |

## 5. 安全注意

官方明确警告："**Bash permission patterns that try to constrain command arguments are fragile.**"

- `Bash(curl https://example.com/*)` 阻不住 `curl -X GET https://example.com/...`、`curl\thttps://...`、`$(which curl) https://...` 等变体
- 真正的安全边界靠 **`deny` 规则 + 工具选择**（用 `WebFetch` 代替 `curl` 可获得更强隔离）

本仓库 `settings.base.json` 的 `deny` 清单：

```
Bash(git push --force:*)
Bash(git push -f:*)
Bash(rm -rf /:*)
Bash(rm -rf ~:*)
Bash(rm -rf ~/:*)
Read(./.env)
Read(./.env.local)
```

## 6. 来源

- [Claude Code Permissions](https://code.claude.com/docs/en/permissions.md)
- [Claude Code Permission Modes](https://code.claude.com/docs/en/permission-modes.md)
- [Claude Code Settings](https://code.claude.com/docs/en/settings.md)
- [Claude Code Server-Managed Settings](https://code.claude.com/docs/en/server-managed-settings.md)
- GitHub issue #24029（permission 自动保存为 `:*` 形式）
- GitHub issue #3428（`:*` 在 settings.local.json 中不生效）
- GitHub issue #10096（规则中间带空格参数导致 settings 失效）
