# claude.ai Routines 云端环境规则

> 本文档由 `claude-code-global` 仓库的 `rules/cloud-routine.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/rules/cloud-routine.md`（CC 端）与 `~/.codex/rules/cloud-routine.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及 claude.ai Routines、云端定时 agent、`RemoteTrigger` / `/schedule` 注册，或需要判断云端 sandbox 能力边界（能不能跑某工具、装某配置、取回输出）时，**必须先把本文件读入上下文**，再开始动手。

云端 sandbox 的能力边界**查不到，只能实测**——与官方文档 / 博客的描述偏差很大，而实测成本不低（要建 routine、要自建回传通道）。本文把实测结论沉淀下来，任何想把开发搬上云端 routine 的项目直接受益、不必重踩。结论实测于 2026-07，云端环境会演进，发现与现状不符时以重新实测为准并回来更新本文。

## 1. 能力矩阵（实测）

| 项                                                                   | 结论                                                                                                                                                    |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `install.sh`（软链 skills/hooks/scripts 到 `$HOME/.claude`）云端执行 | ✅ 跑得通（仅 systemd 注册因容器无 dbus 失败，非致命）                                                                                                  |
| skills 对**已启动**会话生效                                          | ✅ 动态生效——调一次 Skill 工具即整体刷新                                                                                                                |
| hooks（PostToolUse）对已启动会话生效                                 | ✅ 动态生效（实测 ruff format 真的触发）                                                                                                                |
| hooks（SessionStart）                                                | ❌ 已过触发时点                                                                                                                                         |
| **用户级 `~/.claude/CLAUDE.md`**                                     | ❌ 只落地成文件，**不进系统提示**                                                                                                                       |
| **仓库自带 `CLAUDE.md`**                                             | ✅ **自动进系统提示**（`project instructions` 形式）                                                                                                    |
| `gh` CLI                                                             | ❌ **根本未安装**（不是未认证），`glab` 同理                                                                                                            |
| raw GitHub REST API                                                  | ❌ 403，应用层主动拒绝                                                                                                                                  |
| 读 issue / 开 PR                                                     | ✅ 走**环境内置的 GitHub MCP**（工具确切名称以当次会话可见的工具列表为准，不凭记忆硬猜）                                                                |
| 私有仓克隆                                                           | ✅（需在 routine 的 `sources` 里声明）                                                                                                                  |
| 凭证机制                                                             | `~/.gitconfig` 的 `insteadOf` 把 `https://github.com/` 透明改写到 `127.0.0.1` 本地代理，**代理持凭证 + 做仓库级授权**；agent 手里没有可外泄的通用 token |
| 运行环境                                                             | root 用户，`$HOME=/root` 但 `pwd=/home/user`（**两者不一致**），node 22 / Python 3.11 / git 2.43，无 systemd/dbus                                       |
| 输出回读                                                             | ❌ **无编程可读回路**：`RemoteTrigger` 的 `get` 不回运行输出，claude.ai 页面 WebFetch 一律 403。**任何 routine 必须自带汇报出口**（PR / issue 评论）    |
| 其它硬限制                                                           | 无自定义镜像（`anthropics/claude-code#47856` 仍开着）；cron 最小间隔 1 小时且走 UTC                                                                     |

**一个额外的坑**：`install.sh` 跑完后 skill 列表是**替换不是合并**——环境内置的 `dataviz` / `xlsx` / `pdf` 等消失，只剩仓库里的那些。给 routine 写逻辑时别指望内置 skill 还在。

## 2. 推荐做法：三层组合

给一条云端 routine 配置环境时，按三层各取其正解：

1. **指令层：仓库自带 `CLAUDE.md`**。这是唯一会自动进系统提示的指令通道（用户级 `~/.claude/CLAUDE.md` 在云端不生效，见矩阵）。routine 的行为逻辑放仓库内（skill / `CLAUDE.md`），claude.ai 网页上的 prompt 只留指针——逻辑随 PR 被 review、有版本历史，不与网页配置漂移。
2. **工具链层：`git clone && bash install.sh`**。skills / hooks（PostToolUse）对已启动会话动态生效，clone + install 后即可用本仓的 slash commands；SessionStart hook 已过触发时点，别依赖它做云端初始化。
3. **平台能力层：内置 GitHub MCP + routine 的 `sources`**。issue / PR 交互一律走 MCP（`gh` 未装、REST API 被 403，包装它们的本机 helper 一概不可用）；要访问的私有仓在 `sources` 里声明。

## 3. 设计约束：汇报出口

云端**没有编程可读的运行输出回路**（矩阵「输出回读」行），所以 routine 的产出必须自带出口——PR 或 issue 评论是仅有的两条稳路。设计 routine 时先想清楚「结果从哪里回到人眼前」，再写逻辑；没有 diff 就开不出 PR 的场景（如纯巡检报告），出口只剩 issue 评论。
