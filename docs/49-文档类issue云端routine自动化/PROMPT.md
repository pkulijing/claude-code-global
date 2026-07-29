# PROMPT：文档类 issue 的云端 routine 自动化开发

> 来源：`the-foundation` 仓库 [round 0 · routine 自动化框架选型](https://github.com/pkulijing/the-foundation) 的结论落地。
> 本轮是该轮 SUMMARY §8「后续 TODO」第 1 / 2 / 3 条在 `claude-code-global` 的实现。

## 一、背景

`the-foundation` round 0 讨论清楚了「让 AI 自动化地做 routine 事情」的选型，结论是：

- **不引入任何框架**，用 Claude Code 自带的 **claude.ai Routines**（云端定时 agent），
  以「`git clone` + `bash install.sh`」在云端复现开发环境；
- 该链路——**拉 issue → 分诊 → 改代码 → push → 开 PR**——已经过两轮云端探针**实测全程可行**；
- **回路不需要 IM 审批闸，PR 本身就是审批闸**：routine 出 PR → 手机收到推送 → 人在手机上决定合不合。

round 0 只做了选型与能力实测，**没有写任何一条真 routine**。其 TODO 清单第 1 条即为本轮的正题。

round 0 实测确认的云端环境事实（本轮设计的硬约束）：

| 事实                                                      | 对本轮的含义                                       |
| --------------------------------------------------------- | -------------------------------------------------- |
| `install.sh` 云端可跑，skills / hooks **动态生效**        | 云端能复用本仓的 `/quick` `/commit` `/review-loop` |
| 仓库自带 `CLAUDE.md` **自动进系统提示**；用户级的**不进** | 宪法靠仓库 `CLAUDE.md` 生效，不能指望 `~/.claude/` |
| `gh` CLI **根本未安装**，raw GitHub REST API **403**      | `scripts/platform_issue.py` 云端不可用             |
| GitHub MCP **环境内置**，可读 issue / push / 开 PR        | 云端的 issue 交互必须走 MCP                        |
| 凭证在本地代理里、只授权本 session 的仓                   | 安全姿态好，但也意味着够不到未挂 `sources` 的仓    |
| **无编程可读回路**（`RemoteTrigger.get` 不回运行输出）    | routine 必须自带汇报出口，PR 就是出口              |
| cron **最小间隔 1 小时**、表达式走 **UTC**                | 「每天一次」要按 UTC 换算北京时间                  |
| skill 列表是**替换不是合并**（install 后只剩本仓的）      | routine 只能用本仓 skill，用不了内置 `dataviz` 等  |

## 二、本轮要解决的问题

把上面这条已验证可行、但尚未落地的链路，**变成一条每天真跑、产出可合 PR 的 routine**，并解决三个具体诉求。

### 诉求 1：每天自动扫 issue，纯文档类的走 `/quick` 链路做掉并提 PR 到 master

- 触发：每天一次（cron，云端 routine）。
- 范围：**纯文档类**需求——只改 `rules/*.md`、`GLOBAL_AGENTS.md`、`docs/`、`README.md` 这类
  「写规则 / 写说明」的 issue，不碰 `install.sh` / `hooks/` / `scripts/` / `templates/` 的可执行面。
- 形态：**对标 `/quick` 而非 `/start`**——没有人在环时跑三件套只会产出无人读的 `PLAN.md`。
- 产出：向 `master` 提 PR，PR 即审批闸。

### 诉求 2：合理合批，不要一个 issue 一个 PR

当前仓里这类 issue 存量就有十几条（`type:docs` + `area:doc`），一条一个 PR 会把 PR 列表淹掉。
要求：

- **不要 1 issue = 1 PR**；
- 也**不强求每天只出 1 个 PR**——按主题 / 落点自然聚类，合理即可；
- 换言之需要一套「怎么分批」的判断规则，而不是硬编码的数量上限。

### 诉求 3：PR 批准后要 FF 合入，不要 merge commit

用户明确不喜欢 GitHub 原生的 PR 合并方式：Merge 会留 merge commit，历史不再是直线。
本仓一贯的偏好是 **FF 直线历史**（`/rebase`、`/finish` 的 worktree 收尾都按 FF 做）。

诉求是：**照常提 PR（保留手机上 review + 批准这个闸），但「批准」这个动作触发的是一次真正的
fast-forward，而不是 GitHub 的 merge**。需要给出可行机制并落地。

## 三、约束与边界

- **routine 逻辑必须版本化进本仓**（round 0 TODO 第 2 条）：claude.ai 上的 routine prompt 只写
  一句「clone + install + 读某个文件并执行」，真逻辑留在仓库里随 PR 被 review，避免配置漂移。
  这与「issue 是单一真源」是同一个偏好。
- **云端 / 本机的 issue 交互分野必须写清**（round 0 TODO 第 3 条）：本机走
  `scripts/platform_issue.py`，云端走 GitHub MCP。
- **无人在环下不许停下等人**：本仓多个 skill（`/quick` 的前置判断、`/review-loop` 的两轮闸口、
  `/commit` 的 lint 失败）都会「停下来问用户」。routine 里没有用户，这些分岔必须有明确的
  无人值守行为（跳过 / 降级 / 写进 PR 描述），绝不能挂死。
- **已知 P0 缺陷不在本轮修**：issue #60（`/code-review` 因 `disable-model-invocation` 无法被模型调用）
  会让云端的 review 闸走降级链。本轮只需保证降级路径明确且在 PR 里如实标注，修复另开轮次。
- **`claude-code-global` 是云端 agent 的信任根**：routine 每天 clone + install 这个公开仓，
  谁能推它的 master 谁就能改云端 agent 的行为。本轮引入的任何自动写 master 的机制
  （如 FF 合并的 CI）都要把这层风险算进去。

## 四、验收标准

1. 仓库里有一份**版本化的 routine 剧本**，claude.ai 上的 routine 只需一句话指向它。
2. 剧本对「怎么选 issue、怎么分批、怎么开发、怎么提 PR、无人值守时各分岔怎么走」有明确规定，
   且**可在本机手动试跑**以便验证，不必等 cron。
3. PR 的批准动作能落成 **master 上的一次 fast-forward**（无 merge commit、历史直线），
   且该机制经过**实证验证**而非仅凭文档推断。
4. 重复触发是安全的：同一条 issue 不会被两个 PR 同时做。
5. README / CLAUDE.md 等仓库自述同步更新，新增目录与机制可被后来者（含 agent）读懂。
