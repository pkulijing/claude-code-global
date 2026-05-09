#!/usr/bin/env bash
# claude-code-global 自动同步脚本
#
# 设计:被两种触发方共用 ——
#   1. OS 调度器 (macOS launchd / Linux systemd timer):无 flag,日志为主
#   2. Claude SessionStart hook:--session,stdout 出版本摘要 + 更新提醒
#
# 30min 节流共享(~/.claude/.auto-update-last-run),两边互不重复。
# 详细设计见仓库 docs/16-自动同步全局配置/PLAN.md。

set -uo pipefail

# ---------- 自定位仓库根 ----------
# 脚本本体在 <repo>/scripts/auto-update.sh,被软链到 ~/.claude/scripts/。
# 解析自身真实路径(macOS 的 readlink 不支持 -f,手动循环解软链)。
SELF="${BASH_SOURCE[0]}"
while [ -L "$SELF" ]; do
    LINK="$(readlink "$SELF")"
    case "$LINK" in
        /*) SELF="$LINK" ;;
        *)  SELF="$(cd "$(dirname "$SELF")" && pwd)/$LINK" ;;
    esac
done
REPO_DIR="$(cd "$(dirname "$SELF")/.." && pwd)"

# ---------- 常量 ----------
THROTTLE_SEC=1800   # 30 分钟
LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/auto-update.log"
STAMP_FILE="$HOME/.claude/.auto-update-last-run"
mkdir -p "$LOG_DIR"

# ---------- 参数解析 ----------
MODE="background"   # background | session
if [ "${1:-}" = "--session" ]; then
    MODE="session"
fi

# ---------- 日志辅助 ----------
ts() { date "+%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(ts)] $*" >> "$LOG_FILE"; }

# ---------- 退出原因 + 版本摘要 ----------
SKIP_REASON=""    # 非空表示被跳过(仅用于 --session 模式输出)
UPDATED=0         # 1 表示本次实际 pull 到了新 commit
BEFORE_HASH=""
AFTER_HASH=""

extract_repo_path() {
    # 从 origin URL 提取 owner/repo (兼容 https / ssh)
    local url="$1"
    echo "$url" \
        | sed -E 's|^https?://github.com/||; s|^git@github.com:||; s|\.git$||'
}

print_session_summary() {
    [ "$MODE" = "session" ] || return 0

    local origin_url repo_path commit_url compare_url
    origin_url="$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"

    if [ -n "$origin_url" ] && echo "$origin_url" | grep -q "github.com"; then
        repo_path="$(extract_repo_path "$origin_url")"
    else
        repo_path=""
    fi

    local short_after="${AFTER_HASH:0:7}"
    local short_before="${BEFORE_HASH:0:7}"

    if [ "$UPDATED" = "1" ]; then
        echo "🔄 claude-code-global 已更新: $short_before → $short_after"
        if [ -n "$repo_path" ]; then
            echo "   https://github.com/$repo_path/compare/$short_before...$short_after"
        fi
        echo "   ⚠️  本会话尚未应用新配置,/exit 重开后生效"
    elif [ -n "$SKIP_REASON" ]; then
        echo "⚠️  claude-code-global 跳过自动同步: $SKIP_REASON"
        if [ -n "$short_after" ]; then
            local line="   ✅ 当前版本 @ $short_after"
            [ -n "$repo_path" ] && line="$line — https://github.com/$repo_path/commit/$short_after"
            echo "$line"
        fi
    else
        echo "✅ claude-code-global @ $short_after"
        if [ -n "$repo_path" ]; then
            echo "   https://github.com/$repo_path/commit/$short_after"
        fi
    fi
}

# 所有路径退出前都走这里
finish() {
    local exit_code="${1:-0}"
    print_session_summary
    exit "$exit_code"
}

# ---------- 安全检查 ----------
if [ ! -d "$REPO_DIR/.git" ]; then
    log "skip: $REPO_DIR is not a git repo"
    SKIP_REASON="not a git repo"
    finish 0
fi

cd "$REPO_DIR"

# 记录当前版本(无论后续是否拉取,都用于摘要)
BEFORE_HASH="$(git rev-parse HEAD 2>/dev/null || true)"
AFTER_HASH="$BEFORE_HASH"

# 节流(共享时间戳)
NOW="$(date +%s)"
if [ -f "$STAMP_FILE" ]; then
    LAST="$(cat "$STAMP_FILE" 2>/dev/null || echo 0)"
    DIFF=$((NOW - LAST))
    if [ "$DIFF" -lt "$THROTTLE_SEC" ]; then
        # 节流命中不算"跳过原因",对 --session 来说就是常规无更新
        finish 0
    fi
fi

# 必须在 master 分支(避免在临时分支意外 pull)
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [ "$BRANCH" != "master" ]; then
    log "skip: not on master (current: $BRANCH)"
    SKIP_REASON="not on master (current: $BRANCH)"
    finish 0
fi

# dirty working tree → 跳过
if ! git diff --quiet || ! git diff --cached --quiet; then
    log "skip: dirty working tree (run: cd $REPO_DIR && git status)"
    SKIP_REASON="dirty working tree"
    finish 0
fi

# 必须有 origin remote
if ! git remote get-url origin >/dev/null 2>&1; then
    log "skip: no origin remote configured"
    SKIP_REASON="no origin remote"
    finish 0
fi

# fetch
if ! git fetch --quiet origin master 2>>"$LOG_FILE"; then
    log "skip: git fetch failed (network?)"
    SKIP_REASON="git fetch failed"
    finish 0
fi

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/master)"

# 已经最新
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$NOW" > "$STAMP_FILE"
    log "ok: already up to date @ ${LOCAL:0:7}"
    finish 0
fi

# 必须能 fast-forward(LOCAL 是 REMOTE 的祖先)
if ! git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
    log "skip: non-fast-forward (local has unpushed commits?)"
    SKIP_REASON="non-fast-forward (local has unpushed commits)"
    finish 0
fi

# pull + install
log "pulling: ${LOCAL:0:7} → ${REMOTE:0:7}"
if ! git pull --ff-only --quiet origin master >>"$LOG_FILE" 2>&1; then
    log "error: git pull failed"
    SKIP_REASON="git pull failed"
    finish 0
fi

AFTER_HASH="$(git rev-parse HEAD)"

log "running install.sh"
if [ "$MODE" = "session" ]; then
    bash "$REPO_DIR/install.sh" >>"$LOG_FILE" 2>&1
else
    # 后台模式:同时写日志(stdout 通常被 launchd/systemd 捕获到日志)
    bash "$REPO_DIR/install.sh" 2>&1 | tee -a "$LOG_FILE"
fi

INSTALL_EXIT="${PIPESTATUS[0]:-$?}"
if [ "$INSTALL_EXIT" -ne 0 ]; then
    log "error: install.sh exited $INSTALL_EXIT"
    SKIP_REASON="install.sh failed (see log)"
    finish 0
fi

UPDATED=1
echo "$NOW" > "$STAMP_FILE"
log "ok: updated to ${AFTER_HASH:0:7}"
finish 0
