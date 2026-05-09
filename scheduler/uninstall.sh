#!/usr/bin/env bash
# 取消 OS 调度器注册(逃生舱)。

set -uo pipefail

YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }

OS="$(uname -s)"

case "$OS" in
    Darwin)
        plist="$HOME/Library/LaunchAgents/com.claude-code-global.auto-update.plist"
        if [ -f "$plist" ]; then
            launchctl unload "$plist" 2>/dev/null || true
            rm -f "$plist"
            success "已移除 launchd 调度器"
        else
            warn "未找到 plist,无需移除"
        fi
        ;;
    Linux)
        if command -v systemctl >/dev/null 2>&1; then
            systemctl --user disable --now claude-code-global-auto-update.timer 2>/dev/null || true
            rm -f "$HOME/.config/systemd/user/claude-code-global-auto-update.timer"
            rm -f "$HOME/.config/systemd/user/claude-code-global-auto-update.service"
            systemctl --user daemon-reload 2>/dev/null || true
            success "已移除 systemd user timer"
        else
            warn "未检测到 systemd,无操作"
        fi
        ;;
    *)
        warn "不支持的 OS: $OS"
        ;;
esac
