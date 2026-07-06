> 来自 [#24 把「codex review 循环」纳入开发生命周期（执行阶段迭代 review-fix 至 clean，codex 优先 / 不可用降级 CC 自审）](https://github.com/pkulijing/claude-code-global/issues/24)
> Labels: `type:feat` `area:skill` `priority:P1`

# 需求：把「codex review 循环」纳入开发生命周期

## 背景

来源：teleop-operator `round 12`（VR 头手延迟逐增修复，含一处 grpc.aio 消费迁专用线程的多线程重构）。teleop-operator 在内网 GitLab，无公开 URL；本地仓 `~/Work/teleop-operator`。

## 动机（本轮硬实证）

该轮把 VR 的 grpc.aio server-streaming 消费从主事件循环迁到专用 OS 线程（多线程 + 跨线程 asyncio 生命周期管理）。

- Claude Code **自审**只发现 2 个并发隐患；
- 随后让 **codex（独立模型）review**，又补出 3 个 P1——其中最关键的「优雅停不可达」（去掉 cancel 兜底后，stop 信号唤不醒阻塞在 `channel_ready` / `async for` 的协程，join 必超时）CC **完全漏判**；
- 修完 codex 复审判定可提交。

**核心教训**：同一个模型自审自写的代码，盲区一致、极难发现问题——尤其多线程 / 并发 / 复杂逻辑这类「难复现」改动。引入独立的第二个模型（codex）做 review，价值被硬实证。`/code-review`（CC 自审自己的 diff）单独解决不了这个问题，因为是同一个脑子。

## 目标：把「review 循环」立为执行阶段的迭代环

不是 finish 里的一次性动作，而是**执行 → 总结之间的迭代环**：

> 开发到一个 commit 点 → review（codex 优先）→ 发现问题 → 再开发 → 再 commit → 再 review → 直到 review clean（无 P 级问题）→ 才进总结 / 收尾。

关键点：

- **是循环，不是单次**：review 出问题就修、再 review，迭代收敛到干净。
- **位置在「执行 → 总结」之间**，不绑死在 finish（finish 是收尾，review 循环可能跑很多轮）。
- **触发**：重要 / 复杂 / 并发 / 安全相关改动默认走；琐碎改动可跳过（开发者判断或按改动特征）。

## 降级（codex 不可用时）

codex 不可用（未登录 / token 失效 / 离线）时，**降级到 CC 自己的 `/code-review`（self-review）**，并**明确告知「本次是自审、盲区大、未经独立模型把关」**——绝不因 codex 不可用就跳过 review 这一环。（本轮实测踩到过 codex token 失效；当时是停下让用户重登录，但更 robust 的是自动降级 + 标注降级状态，不阻断流程。）

**优先级**：codex 独立 review > CC 自审 > 不 review。

## 候选落点（供 PLAN 阶段决策）

- **A. 新 skill（如 `/review-loop`）**：封装 commit → review（codex 优先、不可用降级 CC）→ 呈现问题 → 等修 → 再循环。复用现有 `codex:rescue` 做 review、`codex:rescue --resume` 做复审（本轮就是这么跑的，体验顺）。
- **B. 写进开发宪法**（`GLOBAL_AGENTS.md` 开发模式的「执行」环节）：把「复杂 / 并发改动，执行收尾走 review 循环（codex 优先、降级 CC）再进总结」立为约定。
- **C. 触发式提示**（hook 或约定）：检测并发 / 复杂改动特征时，主动提示走 review 循环。

issue 作者倾向：**A + B 组合可能最佳**——宪法立约定（B），skill 给可调用的编排（A），hook（C）做轻提醒。

## 范围与约束

- 本仓库是 `claude-code-global`：双轨部署（CC `~/.claude/` + Codex `~/.codex/`）。任何新增 skill / 宪法改动都要考虑两端语义一致。
- 复用既有 `codex:*` 生态（`codex:rescue` / `codex:setup` / `codex:codex-cli-runtime`），不重复造 codex 调用轮子。
- 遵循「文档中并列项平等呈现」「可执行配置不能塞多变体让用户自选」等既有反馈约定。
