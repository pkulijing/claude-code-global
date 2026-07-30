# 定时唤起无头 Agent 任务规则（本机 OS 层）

> 本文档由 `claude-code-global` 仓库的 `playbooks/scheduled-agent.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/playbooks/scheduled-agent.md`（CC 端）与 `~/.codex/playbooks/scheduled-agent.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及**设计或部署「定时 / 周期性唤起一个无头 Agent 干活」的任务**（launchd / systemd timer / cron + `claude -p` 之类）时，**必须先把本文件读入上下文**，再开始动手。

> **与 `playbooks/cloud-routine.md` 的分工**：本文管**跑在自己机器上**的定时无头 agent（OS 定时器拉起本地 `claude -p`）。跑在 claude.ai Routines 云端 sandbox 里的定时 agent 是另一套能力边界（无 `gh`、无输出回路、cron 最小 1 小时且走 UTC……），看那一份。两者共享「无人值守就没有人可问」这条纪律，但**执行环境完全不同，别混用结论**。

「定时唤起一个无头 Coding Agent 干周期性杂活」这个场景会反复出现（飞书文档库每日自动整理、多仓 dev 分支定时同步、本仓的配置自动同步……）。每次重新回忆 launchd / systemd 的差异和那堆坑很浪费，故沉淀为通用流程。

## 1. 四层架构

把任务拆成四层，**每层只干一件事**——这样出问题时能一眼定位是哪层坏了，也让最贵的那层（agent）做最少的事：

1. **OS 定时器（纯闹钟）**：macOS launchd / Linux systemd user timer。只负责「到点了拉起 wrapper」，不含任何业务逻辑。
2. **wrapper 脚本 `run_<job>.sh`**：显式 `export PATH`、`cd` 到工作目录、按日期落日志、记录退出码。定时环境与交互 shell 差别极大，这层是**唯一**能吸收这种差别的地方。
3. **无头 agent**：`claude -p "$(cat <job>.md)" --model <便宜档> --allowedTools <最小白名单> --max-turns N`。**只负责需要判断的步骤**。
4. **确定性脚本**：扫描 / diff / 重建这类工作放普通脚本——零 token、行为可预测、可单独测试。

**分层的收益全在第 3、4 层的切分上**：agent 的 prompt 只编排「跑脚本 → 对差异做判断 → 通知」，不亲自去遍历文件、拼字符串。凡是能写成确定性脚本的，就不该花 token 让模型每次重新推一遍。

## 2. 双平台差异速查

|            | macOS launchd                              | Linux systemd（user）                           |
| ---------- | ------------------------------------------ | ----------------------------------------------- |
| 单元文件   | `~/Library/LaunchAgents/<label>.plist`     | `~/.config/systemd/user/<name>.{service,timer}` |
| 定时语法   | `StartCalendarInterval`                    | `OnCalendar=*-*-* HH:MM:SS`                     |
| 错过补跑   | 睡眠错过 → 唤醒补跑；**关机跳过**          | `Persistent=true` 开机补跑                      |
| 免登录运行 | 默认可                                     | 需 `loginctl enable-linger`                     |
| 装载       | `launchctl bootstrap gui/$(id -u) <plist>` | `systemctl --user enable --now <name>.timer`    |
| 适用宿主   | 常开台式 Mac；**合盖笔记本不适用**         | 常开工作站（首选）                              |

## 3. 实战坑清单

### 3.1 CC 会话内的 `CronCreate` 是 session-only，不能当持久机制

会话退出即失效、且有过期时间。**持久定时必须落到 OS 层**（launchd / systemd）。会话内的定时只适合「这一轮里等一会儿再看」。

### 3.2 宿主选择是第一问，且只能有一个权威副本

- **笔记本合盖即停**，默认应推荐常开工作站；
- **双宿主并跑会重复处理**——状态基线文件（记录「上次处理到哪」的那个文件）**只能有一份权威副本**。迁移宿主时**旧宿主必须先卸载**，否则两台机器各按各的基线跑，产出互相打架。

### 3.3 定时环境的 PATH 极简，wrapper 必须显式 export

launchd / systemd 拉起的进程**不走**你的 `.zshrc` / `.bashrc`。`~/.local/bin`、`/opt/homebrew/bin` 这些全都不在 PATH 里——`claude` 命令本身往往就是第一个「找不到」的。**wrapper 里显式 export，别指望继承。**

### 3.4 无头 agent 三要素

- **显式降档模型**：周期性杂活用便宜档，且**永远显式传**（不传就跟着默认走，默认会随版本漂移）；
- **`--allowedTools` 最小白名单**：无人值守时权限就是风险面；
- **绝不对 `confirmation_required` 追加 `--yes`**：这条要**写进 prompt 作硬约束**。无人值守下「自动确认一切」等于把所有护栏一次性拆掉。

### 3.5 安全门禁会拦住 Agent 自己装定时任务——这是特性不是缺陷

实测：Agent 直接写 `~/Library/LaunchAgents`、或在脚本里拉起无头 `claude`，会被 auto-mode classifier 拦下。

**正确的流程是「Agent 备齐所有文件 + 用户亲手执行安装命令」**——登录持久化理应由人亲手装。别想着绕过它；把安装命令整理清楚给用户即可——安装命令通常又长又多步，**写成一个短路径脚本、只给用户一条 `bash ~/x.sh`**，别让用户去复制会被终端折行粘断的长命令。

### 3.6 通知回路必须闭环

任务收尾**必须发通知**：成功发摘要，失败发原因 + 修复提示（如「token 失效，需重新 `auth login`」）。

没有通知回路的定时任务会**静默失败很多天而无人察觉**——而这正是定时任务最典型的死法：它不报错，它只是不再产出，而「没有产出」和「本来就没什么可做」从外面看一模一样。

### 3.7 认证按机器隔离，迁移宿主要重新认证

lark-cli 的 user token、`claude` 的登录态等都**按机器隔离**，拷配置文件不可靠。新机器上重新认证，不能只搬文件——这一步要算进「迁移宿主」的清单里，否则迁完当晚任务就会因认证缺失而静默失败（正好撞上 §3.6 那个「不报错、只是不再产出」的死法）。
