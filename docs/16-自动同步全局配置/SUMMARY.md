# SUMMARY — 自动同步全局配置

## 背景

多设备(3 台,未来更多)开发 claude-code-global 时,每次换设备都要手动 `git pull && bash install.sh` 才能拿到最新配置,体验割裂。希望 OS 层定时自动 pull + install,且 Claude 启动时主动反馈当前版本和更新状态(更新了要提醒重启会话)。

## 实现方案

### 关键设计

1. **双触发,共用一个底层脚本**:
   - macOS launchd LaunchAgent / Linux systemd user timer:登录跑 + 每小时跑(后台模式)
   - Claude SessionStart hook:每次新 session 启动跑(--session 模式,出版本摘要)
   - 共用 [scripts/auto-update.sh](../../scripts/auto-update.sh),共享 30min 节流时间戳(`~/.claude/.auto-update-last-run`),互不重复

2. **自定位仓库根**:脚本本体住在 `<repo>/scripts/auto-update.sh`,被软链到 `~/.claude/scripts/`。脚本通过 `readlink` 循环解软链拿真实路径,再 `dirname ../..` 拿仓库根 —— 跨设备 clone 到不同目录都能 work,无硬编码。

3. **--session 模式输出三态**:
   - 有更新 → `🔄 已更新: 短hash → 短hash` + GitHub compare URL + ⚠️ 重启提醒
   - 无更新 → `✅ @ 短hash` + GitHub commit URL(每次 SessionStart 都让用户知道当前版本)
   - 跳过 → `⚠️ 跳过自动同步: 原因` + 当前版本 + URL

4. **dirty / non-ff / 网络错误统一策略**:跳过 + 写日志 + **不更新时间戳**(下次还会重试,达到「commit 完下次自动同步」效果);后台模式纯日志静默,SessionStart 模式额外报告原因到 stdout。

5. **install.sh 集成**:末尾自动调 [scheduler/install.sh](../../scheduler/install.sh),失败 warn 不阻塞主 install。`scheduler/install.sh` 检测 OS 走 launchd / systemd 分支,均幂等(先 unload/disable 再 load/enable)。

### 开发内容概括

新增:

- [scripts/auto-update.sh](../../scripts/auto-update.sh) — 主脚本,~170 行,含安全检查、节流、模式分支、版本摘要
- [scheduler/install.sh](../../scheduler/install.sh) — OS 检测 + 调度器注册
- [scheduler/uninstall.sh](../../scheduler/uninstall.sh) — 取消注册(逃生舱)
- [scheduler/launchd.plist.template](../../scheduler/launchd.plist.template) — macOS LaunchAgent 模板
- [scheduler/systemd.service.template](../../scheduler/systemd.service.template) + [timer.template](../../scheduler/systemd.timer.template) — Linux systemd user units

修改:

- [settings.base.json](../../settings.base.json) — 加 SessionStart hook(matcher: startup,timeout 60s,managed marker `# @claude-code-global:auto-update`)
- [install.sh](../../install.sh) — 末尾调 `scheduler/install.sh`
- [CLAUDE.md](../../CLAUDE.md) — 目录结构段加 `scripts/` 和 `scheduler/` 说明

### 额外产物

- 详细的 PROMPT.md / PLAN.md 记录设计取舍(三轮迭代:从 SessionStart-only → OS 调度器-only → 双保险)
- launchd plist 显式声明 `EnvironmentVariables.PATH`,避免 launchd 默认 PATH 缺 `/opt/homebrew/bin` 导致 git/jq 找不到

### 验证

跑了 install.sh 完整流程并模拟分支:

| 分支                                            | 结果                                                        |
| ----------------------------------------------- | ----------------------------------------------------------- |
| `bash install.sh` 集成 launchd 注册             | ✅ `launchctl list` 列出 com.claude-code-global.auto-update |
| settings.json SessionStart hook 落地            | ✅ jq 验证                                                  |
| plist 模板占位符 `{{REPO_DIR}}` `{{HOME}}` 替换 | ✅ 渲染后路径正确                                           |
| dirty wt + --session                            | ✅ 输出 `⚠️ 跳过... + ✅ 当前版本 @ + URL`                  |
| 节流命中 + --session                            | ✅ 输出 `✅ @ + URL`                                        |
| 节流命中 + 后台模式                             | ✅ stdout silent                                            |
| 干净 wt + LOCAL=REMOTE(完整 fetch 走通)         | ⏳ 待自然观测(dogfood 环境无法清干净)                       |
| 干净 wt + 有 ff 更新(完整 pull + install)       | ⏳ 待自然观测(下次推 commit 后 launchd 跑到即知)            |
| Linux systemd 分支                              | ⏳ 待 Linux 设备实测                                        |

> 用户表示后续自行验证(本次 commit 推上去后多设备跑一跑即知),问题应不大 —— 三个待观测分支的代码路径都很短,主要是真实环境的 `git fetch` / `git pull` / `bash install.sh` 串联。

## 局限性

1. **第一台设备首次仍要手动**:`git clone + bash install.sh` 是 hook 自举的硬限制,无法绕过
2. **正在跑的旧 Claude session 不会自动应用新配置**:Claude hook 只在 session 启动时注册,这是 Claude 的限制 —— 我们的方案是 SessionStart 模式下用 ⚠️ 文案提醒用户 `/exit` 重开
3. **dirty wt 时一直跳过 + 不更新时间戳**:意味着 launchd 每小时都会 dirty skip 写一行日志,长期 dirty 会让日志膨胀。可接受 —— 真实使用场景下 dirty 状态都是短暂的,而且日志旋转不在本轮范围
4. **macOS PATH 假设 Homebrew**:plist 里硬编码了 `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`,intel mac 用户在 `/usr/local/bin` 也有 brew,够用;非 brew 安装的 git 在异常路径会找不到。可接受
5. **Linux 分支未实测**:模板和 install 脚本都按 systemd user timer 标准写,逻辑对应 macOS 分支,但本机无 Linux 环境验证

## 后续 TODO

- 在 Linux 设备上 dogfood 验证 systemd 分支(开新轮)
- 考虑日志旋转:超过某 size 自动 truncate 或按周分文件(P2,日志膨胀实际触发后再做)
- `scheduler/install.sh` 加 `--dry-run` flag,方便排查时看会写啥不实际改系统(P2)
- 如果将来想支持「不在 master 也能自动 pull」(比如长期工作分支自动 rebase remote),需要更精细的策略,本轮明确不做
