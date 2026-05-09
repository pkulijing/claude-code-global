# PLAN — 自动同步全局配置

## 总体设计

```
仓库 scripts/auto-update.sh        ← 单一实现,所有触发方共用
    ↓ install.sh 软链
~/.claude/scripts/auto-update.sh
    ↑                       ↑
    │                       │
OS 调度器                  SessionStart hook
(launchd / systemd)        (settings.base.json)
   每小时 + 登录            新 session 启动
```

两边共用 30 分钟节流(时间戳文件),互不重复执行。

## 文件清单

新增:

- `scripts/auto-update.sh` — 主脚本(实际拉取 + install)
- `scheduler/install.sh` — 检测 OS,注册 launchd/systemd
- `scheduler/uninstall.sh` — 取消注册(逃生舱)
- `scheduler/launchd.plist.template` — macOS LaunchAgent 模板,含 `{{REPO_DIR}}` 占位
- `scheduler/systemd.service.template` — Linux systemd user service
- `scheduler/systemd.timer.template` — Linux systemd user timer

修改:

- `settings.base.json` — 加 SessionStart hook 条目
- `install.sh` — 末尾调 `scheduler/install.sh`(失败 warn 不阻塞)
- `CLAUDE.md` — 目录结构段加 `scheduler/` 说明

## 关键设计点

### 1. auto-update.sh 仓库根目录定位(跨设备通用)

脚本本体住在 `<repo>/scripts/auto-update.sh`,被软链到 `~/.claude/scripts/auto-update.sh`。脚本通过 `readlink` 解析自身真实路径,再 `dirname ../..` 拿到仓库根 —— 跨设备 clone 到不同目录都能 work。

```bash
SELF="${BASH_SOURCE[0]}"
while [ -L "$SELF" ]; do
    LINK="$(readlink "$SELF")"
    case "$LINK" in
        /*) SELF="$LINK" ;;
        *)  SELF="$(dirname "$SELF")/$LINK" ;;
    esac
done
REPO_DIR="$(cd "$(dirname "$SELF")/.." && pwd)"
```

### 2. 节流(30 分钟,通用)

时间戳文件 `~/.claude/.auto-update-last-run`,记录上次**成功 fetch** 的 unix 时间(用文件内容,不用 mtime,避免被 touch 误改)。

`now - last < 1800` → 直接 exit 0。dirty / non-ff / fetch 失败 都**不**更新时间戳,确保下次还会重试。

### 3. dirty working tree → 写日志

```bash
if ! git diff --quiet || ! git diff --cached --quiet; then
    log "skip: dirty working tree (run: cd $REPO_DIR && git status)"
    exit 0
fi
```

后台跑没有终端输出,所有信息走 `~/.claude/logs/auto-update.log`(append 模式,带时间戳)。

### 4. 安全检查清单(任一不满足则 skip + 日志)

- 仓库目录存在且是 git repo
- 当前在 master 分支
- 配置了 origin remote
- `git fetch origin master` 成功
- `LOCAL` 是 `REMOTE` 的祖先(可 fast-forward)

### 5. 有更新时

- `git pull --ff-only origin master`
- 调 `bash $REPO_DIR/install.sh`
- install.sh 完整输出 → 日志文件
- 写入新时间戳

### 6. --session 模式(Claude SessionStart 用)

flag 定义:

- 无 flag(默认):OS 调度器用,install.sh 输出同时到 stdout 和日志
- `--session`:install.sh 完整输出**只**到日志;stdout 出**精炼版本摘要**(给当前 Claude 会话上下文看)

GitHub URL 解析:从 `git remote get-url origin` 提取 `<owner>/<repo>`,兼容 https / ssh 两种 origin 格式:

```bash
extract_repo_path() {
    local url="$1"
    # https://github.com/owner/repo(.git)?
    # git@github.com:owner/repo(.git)?
    echo "$url" | sed -E 's|^https?://github.com/||; s|^git@github.com:||; s|\.git$||'
}
```

**--session 模式输出格式**:

更新成功(本次拉到了新 commit):

```
🔄 claude-code-global 已更新: abc1234 → def5678
   https://github.com/<owner>/<repo>/compare/abc1234...def5678
   ⚠️  本会话尚未应用新配置,/exit 重开后生效
```

无更新(节流命中 / LOCAL=REMOTE / 跳过等):

```
✅ claude-code-global @ def5678
   https://github.com/<owner>/<repo>/commit/def5678
```

跳过(dirty / non-ff / 网络错误等)— 既报版本也报跳过原因:

```
⚠️  claude-code-global 跳过自动同步: dirty working tree
   ✅ 当前版本 @ def5678 — https://github.com/<owner>/<repo>/commit/def5678
```

origin 不是 GitHub 时(理论不可能,但 defensive):

- URL 不带 `github.com` → 省略 URL 行,只显示 hash

实现思路:

- 在脚本开头记录 `BEFORE_HASH=$(git rev-parse HEAD)`
- 在脚本各退出点之前(更新完 / 跳过 / 节流命中 / 已最新)调用 `print_session_summary` 函数,根据 `AFTER_HASH` 与 `BEFORE_HASH` 是否一致 + 是否有跳过原因决定输出哪种格式
- 非 --session 模式下 `print_session_summary` 是 no-op

### 7. settings.base.json hook 条目

```json
"SessionStart": [
  {
    "matcher": "startup",
    "hooks": [
      {
        "type": "command",
        "command": "bash $HOME/.claude/scripts/auto-update.sh --session # @claude-code-global:auto-update",
        "timeout": 60
      }
    ]
  }
]
```

- `matcher: "startup"`:只在新 session 启动触发(不含 resume / clear / compact)
- `# @claude-code-global:auto-update` 标记 — 符合 install.sh 已有 managed hook 约定
- timeout 60s 留 buffer(慢网下 fetch + install 可能 > 30s)

### 8. macOS launchd plist 模板

`scheduler/launchd.plist.template`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude-code-global.auto-update</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{{REPO_DIR}}/scripts/auto-update.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>StandardOutPath</key>
    <string>{{HOME}}/.claude/logs/auto-update.log</string>
    <key>StandardErrorPath</key>
    <string>{{HOME}}/.claude/logs/auto-update.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

注册:`launchctl load -w ~/Library/LaunchAgents/com.claude-code-global.auto-update.plist`(`-w` 持久启用,重启仍生效;新 macOS 推荐 `bootstrap`,但 `load -w` 兼容性最好)

### 9. Linux systemd user unit

`scheduler/systemd.service.template`:

```ini
[Unit]
Description=Claude Code Global config auto-update

[Service]
Type=oneshot
ExecStart=/bin/bash {{REPO_DIR}}/scripts/auto-update.sh
StandardOutput=append:{{HOME}}/.claude/logs/auto-update.log
StandardError=append:{{HOME}}/.claude/logs/auto-update.log
```

`scheduler/systemd.timer.template`:

```ini
[Unit]
Description=Claude Code Global config auto-update timer

[Timer]
OnStartupSec=1min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

注册:

- 写到 `~/.config/systemd/user/`
- `systemctl --user daemon-reload`
- `systemctl --user enable --now claude-code-global-auto-update.timer`

### 10. scheduler/install.sh 流程

```
检测 $OSTYPE / uname -s:
  darwin* → 走 launchd 分支
  linux*  → 检测 systemctl 是否可用:
              有 → systemd user timer
              无 → 提示用户手动加 cron @hourly(或写个 crontab fallback)
  其他    → warn 退出
```

**幂等**:

- launchd:先 `launchctl unload` 再 `load`(忽略 unload 失败)
- systemd:先 `disable --now` 再 `enable --now`

模板渲染:`sed "s|{{REPO_DIR}}|$REPO_DIR|g; s|{{HOME}}|$HOME|g"`

### 11. install.sh 末尾追加

```bash
# 注册 OS 自动同步调度器(幂等;失败 warn 不阻塞)
if [ -f "$REPO_DIR/scheduler/install.sh" ]; then
    bash "$REPO_DIR/scheduler/install.sh" || warn "调度器注册失败,可手动运行 bash $REPO_DIR/scheduler/install.sh"
fi
```

## 测试用例

shell 脚本,手动场景测试:

| 触发方               | 场景                             | 期望                                            |
| -------------------- | -------------------------------- | ----------------------------------------------- |
| 直接调               | 已是最新                         | silent + 时间戳更新                             |
| 直接调               | 有新 commit 可 ff                | pull + install,日志含 install 输出              |
| 直接调               | dirty wt                         | log: skip + 不更新时间戳                        |
| 直接调               | 不在 master                      | log: skip + 不更新时间戳                        |
| 直接调               | non-ff (本地有未 push 的 commit) | log: skip + 不更新时间戳                        |
| 直接调               | 网络断开                         | log: skip + 不更新时间戳                        |
| --quiet              | 有更新                           | stdout 仅一行 `✅ updated to <hash>`,详情入日志 |
| --quiet              | 已是最新 / 节流命中              | stdout silent                                   |
| 节流                 | 时间戳 < 30min                   | silent exit                                     |
| scheduler/install.sh | 重复跑                           | 幂等,LaunchAgent/timer 替换不报错               |

## 不在范围

- 自动重启正在运行的 Claude session(技术上做不到)
- 自动 commit / stash 本地未提交修改(违反"绝不动用户代码"原则)
- 多分支自动 pull(只在 master)
- 弹 macOS 通知(用户偏好不打扰)
