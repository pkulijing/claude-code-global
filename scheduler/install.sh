#!/usr/bin/env bash
# 注册 OS 调度器(macOS launchd / Linux systemd user timer),让
# scripts/auto-update.sh 自动跑「登录 + 每小时」一次。
#
# 由仓库根 install.sh 自动调用,也支持单独执行。幂等。

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCHEDULER_DIR="$REPO_DIR/scheduler"

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
    sed -e "s|{{REPO_DIR}}|$REPO_DIR|g" -e "s|{{HOME}}|$HOME|g" "$1" > "$2"
}

install_macos() {
    local plist_dst="$HOME/Library/LaunchAgents/com.claude-code-global.auto-update.plist"
    mkdir -p "$HOME/Library/LaunchAgents"

    # 渲染模板
    render_template "$SCHEDULER_DIR/launchd.plist.template" "$plist_dst"

    # 幂等:先 unload(可能不存在,忽略错误),再 load -w(持久启用)
    launchctl unload "$plist_dst" 2>/dev/null || true
    if launchctl load -w "$plist_dst" 2>/dev/null; then
        success "已注册 launchd 调度器(登录跑 + 每小时跑)"
        info "  plist:  $plist_dst"
        info "  日志:    $HOME/.claude/logs/auto-update.log"
    else
        warn "launchctl load 失败,可手动: launchctl load -w $plist_dst"
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
        info "  日志:   $HOME/.claude/logs/auto-update.log"
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
