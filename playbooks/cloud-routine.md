# claude.ai Routines 云端环境规则

> 本文档由 `claude-code-global` 仓库的 `playbooks/cloud-routine.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/playbooks/cloud-routine.md`（CC 端）与 `~/.codex/playbooks/cloud-routine.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
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

## 4. 写剧本：每个「停下问人」的分岔都必须逐条重新规定

既有 skill 在为难时的行为几乎都是**停下来问用户**——`/quick` 的前置判断（这需求是不是该走 `/start`）、`/review-loop` 的每 2 轮人工闸口、`/commit` 的 lint 失败。**有人在环时这是优点；搬进无人值守环境就是挂死**：定时会话里没有用户，agent 会停在那里直到超时，一次运行白跑。

而这些「停下问人」是**隐式契约**——散落在各 skill 的正文里，没人会在搬去 headless 时主动逐条翻出来重新定义。所以：

> **给无人值守 agent 写剧本时，必须把它会调用的每个流程里的每个「停下问人」分岔，逐条映射到一个明确动作**（跳过 / 降级并标注 / 放弃该批），写成剧本里的一张表。**且降级必须留痕，绝不静默。**

现成范例见 `skills/routine-docs/SKILL.md` 与 `skills/routine-slim/SKILL.md` 的「无人值守分岔契约」表（`/start` 分岔、review 降级、lint 失败、push 失败逐条映射；**以那两处为准，此处不复制**）。

新起一条 routine / 无头 agent 任务时照着做一遍这个映射，而不是等挂死了才发现。

## 5. `--dry-run` 是一等公民，上线前必跑

凡「读一批真实数据 → 模型做判断 → 产生外部副作用（提 PR / 发消息 / 改文件 / 调 API）」的自动化 skill，**`--dry-run` 是一等公民而非可选项**。它至少要打印三样：**选中了什么、排除了什么及理由、准备产生哪些副作用**。

**且在首次挂定时 / 上线之前必须先跑一次 dry-run 并由人过目**——把它当成上线检查单的一步，不是「有空再跑跑」。

理由是这类 skill 的质量风险**不在代码，而在判断规则是否贴合真实数据的分布**，而这只能实测。实证：`/routine-docs` 挂 cron 前的 dry-run 跑了真实的 27 条 open issue，当场改掉剧本两条规则——① 缺「仓库现状已满足」这条排除项，照原样跑会把已在文件里的内容再写一遍、产出纯噪音 PR；② 「落 `GLOBAL_AGENTS.md` **或**新增 `playbooks/<topic>.md`」这类落点歧义普遍存在，补了「默认补进现有文档」。**这两个洞纸上推演推不出来**，没有 dry-run 就要等第一个垃圾 PR 污染 issue / PR 列表才暴露。
