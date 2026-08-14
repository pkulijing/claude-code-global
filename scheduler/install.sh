#!/usr/bin/env bash
# 注册 OS 调度器(macOS launchd / Linux systemd user timer),让
# scripts/auto-update.sh 自动跑「登录 + 每小时」一次。
#
# 由仓库根 install.sh 自动调用,也支持单独执行。幂等。

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCHEDULER_DIR="$REPO_DIR/scheduler"

# 选定调度器要服务的 agent home。auto-update.sh 单跑一次即由 install.sh 双轨部署
# CC 与 Codex 两端，所以只需注册一个调度器；AGENT_HOME 只决定日志 / 节流戳的落点。
# 优先 ~/.claude；仅装了 Codex 时取 ~/.codex。
if [ -d "$HOME/.claude" ]; then
    AGENT_HOME="$HOME/.claude"
elif [ -d "$HOME/.codex" ]; then
    AGENT_HOME="$HOME/.codex"
else
    AGENT_HOME="$HOME/.claude"
fi
mkdir -p "$AGENT_HOME/logs"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }

OS="$(uname -s)"

render_template() {
    # render_template <src> <dst>
    sed -e "s|{{REPO_DIR}}|$REPO_DIR|g" \
        -e "s|{{HOME}}|$HOME|g" \
        -e "s|{{AGENT_HOME}}|$AGENT_HOME|g" \
        "$1" > "$2"
}

LAUNCHD_LABEL="com.claude-code-global.auto-update"

# job 是否已加载。实测:`launchctl list <label>` 存在 → 0,不存在 → 113。
# 只判「是否为 0」,不硬编码 113,以免其它 macOS 版本换了码值。
job_is_loaded() {
    launchctl list "$LAUNCHD_LABEL" >/dev/null 2>&1
}

# job 主进程的 PID(job 未加载 / 未在运行时为空)。
job_pid() {
    launchctl list "$LAUNCHD_LABEL" 2>/dev/null \
        | awk -F'= ' '/"PID"/{gsub(/[^0-9]/,"",$2); print $2}' || true
}

# 当前进程是否正跑在该 job 内 —— 沿 ppid 链上溯,命中 job 主进程 PID 即是。
# 实测:launchd 报告的是最外层 auto-update.sh 的 PID,而本脚本是它的孙进程
# (auto-update.sh → install.sh → scheduler/install.sh),链上必然命中。
running_inside_job() {
    local jp p
    jp="$(job_pid)"
    [ -n "$jp" ] || return 1
    p=$$
    while [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null; do
        if [ "$p" = "$jp" ]; then
            return 0
        fi
        p="$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ' || true)"
    done
    return 1
}

install_macos() {
    local plist_dst="$HOME/Library/LaunchAgents/com.claude-code-global.auto-update.plist"
    local tmp_plist
    mkdir -p "$HOME/Library/LaunchAgents"

    if ! command -v launchctl >/dev/null 2>&1; then
        warn "未找到 launchctl,跳过调度器注册"
        return 1
    fi

    # 先渲染到临时文件,好在落盘前跟已装的那份比对
    tmp_plist="$(mktemp)"
    render_template "$SCHEDULER_DIR/launchd.plist.template" "$tmp_plist"

    # ① 已是目标状态(内容一致 + job 已加载)→ 什么都不做。
    #
    # 这条早退不只是省事,它是**安全要求**:本脚本可能正由 auto-update.sh 经
    # launchd 拉起,而 `launchctl unload` 会杀死该 job 名下的全部进程,也就是
    # 执行 unload 的自己 —— 于是 job 被摘掉、下一行 load 永远执行不到,自动同步
    # 从此停摆到下次登录。详见 docs/58-调度器自杀式重注册/。
    if cmp -s "$tmp_plist" "$plist_dst" && job_is_loaded; then
        rm -f "$tmp_plist"
        info "launchd 调度器已注册且配置未变,跳过重注册"
        info "  plist:  $plist_dst"
        info "  日志:    $AGENT_HOME/logs/auto-update.log"
        return 0
    fi

    # 走到这里说明确需(重)注册:plist 内容有变,或 job 掉线了。

    # ② 但如果自己正被该 job 承载,就地 unload 仍会自杀 → 只更新 plist,
    #    把重注册推迟到下次登录(launchd 届时会读到新 plist)。
    if running_inside_job; then
        mv -f "$tmp_plist" "$plist_dst"
        warn "plist 已更新,但当前进程正由该 launchd job 运行"
        warn "  就地重注册会杀死正在运行的自己,故推迟到下次登录自动生效"
        warn "  如需立即生效,可在终端手动跑:"
        warn "    launchctl unload $plist_dst && launchctl load -w $plist_dst"
        return 0
    fi

    # ③ 不在 job 内(人工跑 install.sh / 首次安装)→ 正常重注册
    mv -f "$tmp_plist" "$plist_dst"
    launchctl unload "$plist_dst" 2>/dev/null || true
    launchctl load -w "$plist_dst" 2>/dev/null || true

    # 成败**只认事后查询**。实测 `launchctl load` 在三种失败模式下(路径不存在 /
    # plist 损坏 / 已加载)全部打印 "Load failed" 却仍 exit 0,据其退出码判断会把
    # 失败一路报成成功。
    if job_is_loaded; then
        success "已注册 launchd 调度器(登录跑 + 每小时跑)"
        info "  plist:  $plist_dst"
        info "  日志:    $AGENT_HOME/logs/auto-update.log"
    else
        warn "launchd 调度器注册失败(launchctl list 查不到 $LAUNCHD_LABEL)"
        warn "可手动: launchctl load -w $plist_dst"
        return 1
    fi
}

install_linux() {
    if ! command -v systemctl >/dev/null 2>&1; then
        warn "未检测到 systemd,跳过自动调度器注册"
        warn "可手动添加 cron: (crontab -l 2>/dev/null; echo '@hourly bash $REPO_DIR/scripts/auto-update.sh') | crontab -"
        return 0
    fi

    local unit_dir="$HOME/.config/systemd/user"
    local svc="$unit_dir/claude-code-global-auto-update.service"
    local tmr="$unit_dir/claude-code-global-auto-update.timer"
    mkdir -p "$unit_dir"

    render_template "$SCHEDULER_DIR/systemd.service.template" "$svc"
    render_template "$SCHEDULER_DIR/systemd.timer.template" "$tmr"

    systemctl --user daemon-reload
    # 幂等:先 disable --now(忽略错误),再 enable --now
    systemctl --user disable --now claude-code-global-auto-update.timer 2>/dev/null || true
    if systemctl --user enable --now claude-code-global-auto-update.timer 2>/dev/null; then
        success "已注册 systemd user timer(开机后 1min + 每小时跑)"
        info "  unit:   $svc"
        info "  timer:  $tmr"
        info "  日志:   $AGENT_HOME/logs/auto-update.log"
        info "  状态:   systemctl --user status claude-code-global-auto-update.timer"
    else
        warn "systemctl enable 失败"
        warn "如果不在图形会话中,可能需要先 'loginctl enable-linger $USER' 让 user units 在未登录时也运行"
        return 1
    fi
}

case "$OS" in
    Darwin)
        install_macos
        ;;
    Linux)
        install_linux
        ;;
    *)
        warn "不支持的 OS: $OS,跳过调度器注册"
        warn "可手动添加 cron 或自行配置"
        ;;
esac
