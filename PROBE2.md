# GitHub 可达性探测（读完即可关闭）

一次性探针，探测云端 routine session 对 GitHub 的可达能力边界。本文件本身即为第 7 步「写权限」测试的产物，通过后应直接关闭/删除对应 PR，无需合并。

## 第 1 步：仓库落地情况

`pwd` = `/home/user`，`ls -a` 下有 `claude-code-global` 与 `the-foundation` 两个目录，均已成功克隆。

### claude-code-global

```
origin  http://local_proxy@127.0.0.1:41729/git/pkulijing/claude-code-global (fetch)
origin  http://local_proxy@127.0.0.1:41729/git/pkulijing/claude-code-global (push)
dac8bdc [round 48] docs(finish): 补 SUMMARY 与 DEVTREE，收尾 round 48
```

### the-foundation（私有仓）

```
origin  http://local_proxy@127.0.0.1:41729/git/pkulijing/the-foundation (fetch)
origin  http://local_proxy@127.0.0.1:41729/git/pkulijing/the-foundation (push)
23923db docs: 修正 README 中 open issues 速览链接为按 priority 过滤
```

**结论：私有仓 the-foundation 成功克隆下来了**，remote 指向本地 git 代理（`127.0.0.1:41729`），并非直连 github.com。

## 第 2 步：项目级 CLAUDE.md 是否自动入上下文

**是，自动进入了。** 本次会话开场的 system-reminder 中，`claude-code-global` 与 `the-foundation` 两个仓库的 CLAUDE.md 内容都以「Contents of .../CLAUDE.md (project instructions, checked into the codebase)」的形式自动出现在指令上下文里，未经任何 Read 工具调用。

引用开头两行：

- `claude-code-global` 的 CLAUDE.md 开头：
  ```
  # claude-code-global

  管理 Coding Agent 全局配置（`GLOBAL_AGENTS.md` + `skills/` + `hooks/` + ...
  ```
- `the-foundation` 的 CLAUDE.md 开头：
  ```
  # the-foundation

  借《基地系列》之名的长期思考仓：沉淀方向性讨论与决策，为后续的具体项目提供第一推动。
  ```

两者均在会话首个 system-reminder 中原文出现，属于「自动入上下文」而非「主动 Read」。

## 第 3 步：凭证勘察

`env | grep -iE 'github|gh_|token|credential'`（值已打码）命中的变量名：

```
MAX_THINKING_TOKENS=<REDACTED>
CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR=<REDACTED>
GH_TOKEN=<REDACTED>
GITHUB_TOKEN=<REDACTED>
CLOUDSDK_AUTH_ACCESS_TOKEN=<REDACTED>
GIT_CONFIG_VALUE_2=<REDACTED>
GIT_CONFIG_VALUE_1=<REDACTED>
CLAUDE_SESSION_INGRESS_TOKEN_FILE=<REDACTED>
GIT_CONFIG_KEY_1=<REDACTED>
GIT_CONFIG_KEY_0=<REDACTED>
GIT_CONFIG_KEY_2=<REDACTED>
```

`git config --list --show-origin | grep credential`：仅命中 `credential.interactive=false`（command line 层）。

`~/.git-credentials`：不存在（`cat` 报 No such file or directory）。

`which gh curl python3`：
```
gh: 未找到（command not found）
curl: /usr/bin/curl
python3: /usr/local/bin/python3
```

关键机制（`git config --list --show-origin` 全量）：`~/.gitconfig` 里有

```
url.http://local_proxy@127.0.0.1:41729/git/.insteadof=https://github.com/
```

即：任何 `https://github.com/...` 的 git 操作都会被**透明改写**为走本地 `127.0.0.1:41729` 代理，由代理本身持有并注入凭证——这不是一个暴露在环境变量里、可被读出的通用 GitHub token，而是范围严格限定在「本 session 已授权的仓库」的一层本地转发。

## 第 4 步：匿名读（公开仓，直连 api.github.com）

```
curl -s -o /dev/null -w 'HTTP=%{http_code}\n' https://api.github.com/repos/pkulijing/claude-code-global
HTTP=403
```

不是预期的 200。直连 `api.github.com`（不经由本地 git 代理改写）被拦截，无论仓库公开与否。

## 第 5 步：鉴权读（私有仓）

```
git ls-remote https://github.com/pkulijing/the-foundation
23923db71f8c8cb02af01c218ef75419346c5f7b        HEAD
23923db71f8c8cb02af01c218ef75419346c5f7b        refs/heads/master
```

**成功**——因为 `https://github.com/` 会被 `.gitconfig` 的 `insteadOf` 规则改写到本地代理，代理侧持有凭证并做了仓库级授权检查。

```
curl -s -o /dev/null -w 'HTTP=%{http_code}\n' https://api.github.com/repos/pkulijing/the-foundation
HTTP=403
```

直连 REST API 依旧 403（含私有仓），与是否公开无关——REST API 路径根本没有走那层 git 专用代理改写。

用显式 `-x "$HTTPS_PROXY"` 重试上述两个 API 调用，结果仍是 403，且响应体（而非纯连接失败）为：

```json
{"message": "GitHub access is not enabled for this session. An org admin must connect the Claude GitHub App for this organization.", "documentation_url": "https://docs.anthropic.com/en/docs/claude-code/github-actions"}
```

即：**这是显式的应用层拒绝，不是网络层故障**——原始 GitHub REST/API 通道对本 session 是被主动关闭的，可用的只有 (a) git 协议经由 insteadOf 代理，(b) GitHub MCP server 提供的工具。

## 第 6 步：读 issue

`gh issue list`：`gh: command not found`（未安装）。

`curl` 直连与经 `$HTTPS_PROXY` 均返回同一条「GitHub access is not enabled for this session」拒绝（同第 5 步）。

改用 **GitHub MCP server 工具**（`mcp__github__list_issues`，owner=pkulijing, repo=claude-code-global, state=OPEN, perPage=5）：**成功**，返回 `totalCount: 25`，含 issue #70/#69/#68/#67/#66 等完整标题与正文。

**结论：能拿到 issue 列表，但仅能通过 GitHub MCP server 工具，raw REST API（无论是否走代理）均被应用层拒绝。**
