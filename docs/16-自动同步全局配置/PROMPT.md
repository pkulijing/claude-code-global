# 自动同步全局配置(多设备开发)

## 背景

我现在在 3 台设备上开发,未来可能更多。每次换设备,都要手动:

1. `cd ~/Personal/claude-code-global && git pull`
2. `bash install.sh`
3. (重启正在跑的 Claude session)

第 3 项做不到(hook 只在 session 启动时注册,正在跑的 session 拉不到新配置),
能接受;前两项希望自动化。

## 期望行为

**双保险**:OS 层定时 + Claude SessionStart hook,共用同一个底层脚本。

### OS 层调度(主)

即使没开 Claude 也保持配置最新:

- macOS:launchd LaunchAgent
- Linux:systemd user timer(优先)或 cron 兜底
- 频率:**登录就跑一次 + 每小时跑一次**

### Claude SessionStart hook(兜底 + 版本反馈)

兼两个功能:

1. **兜底**:OS 调度极端情况没跑(比如禁用了 LaunchAgent 或刚开机调度器还没起)时,新 Claude session 启动时再拉一次
2. **每次 SessionStart 都主动反馈**:
   - 如果**这次** SessionStart 触发了更新 → 显眼提醒 + 列出 hash 变化 + GitHub compare 链接 + 提醒 `/exit` 重开本会话才能应用
   - 如果**没更新**(节流命中或本就是最新) → 安静地显示当前版本 hash + GitHub commit 链接(让我随时知道这台机现在是哪个版本)
   - 如果跳过了(dirty 等) → 既显示版本 hash,也显示跳过原因

### 共同行为

- **30 分钟节流**:两边共用一个时间戳文件,30min 内已成功 fetch 过就跳过,避免重复跑
- dirty working tree → 跳过 + **写日志**(`~/.claude/logs/auto-update.log`),不弹通知不打扰
- 网络异常 / non-fast-forward / 不在 master → silent skip + 写日志
- SessionStart 模式加 `--session` flag:install.sh 完整输出只入日志,stdout 出**精炼的版本摘要**(更新前后 hash + GitHub 链接 + 必要时的重启提醒)
- 安装时机:`bash install.sh` 顺手注册 OS 调度器(幂等),用户不需要额外步骤

## 取舍 / 范围

- 第一台设备首次仍要手动 `git clone + bash install.sh`(一次性)
- 不处理「正在跑的旧 Claude session 立即生效」,需要 `/exit` 重开
- 不弹原生通知(用户偏好不打扰)
- Linux 上「登录跑」靠 systemd timer `OnStartupSec` 近似(跨发行版差异大,不强求精确登录触发)
