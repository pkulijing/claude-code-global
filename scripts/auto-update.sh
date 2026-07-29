#!/usr/bin/env bash
# claude-code-global 自动同步脚本
#
# 唯一触发方是 OS 调度器 (macOS launchd / Linux systemd timer),登录跑 + 每小时跑。
# 全程静默,信息走日志;30min 节流($AGENT_HOME/.auto-update-last-run)防重复。
# 详细设计见仓库 docs/16-自动同步全局配置/PLAN.md。

set -uo pipefail

# ---------- 自定位仓库根 ----------
# 脚本本体在 <repo>/scripts/auto-update.sh,被软链到 ~/.claude/scripts/ 与 ~/.codex/scripts/。
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
# AGENT_HOME 指向某个 agent 的配置目录(CC 是 ~/.claude,Codex 是 ~/.codex)。
# 默认 ~/.claude;由 OS 调度器通过环境变量覆盖。
# 日志与节流戳落在该目录下,使 Codex-only 机器也能正常工作。
AGENT_HOME="${AGENT_HOME:-$HOME/.claude}"
THROTTLE_SEC=1800   # 30 分钟
LOG_DIR="$AGENT_HOME/logs"
LOG_FILE="$LOG_DIR/auto-update.log"
STAMP_FILE="$AGENT_HOME/.auto-update-last-run"
mkdir -p "$LOG_DIR"

# ---------- 日志辅助 ----------
ts() { date "+%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(ts)] $*" >> "$LOG_FILE"; }

# ---------- 安全检查 ----------
if [ ! -d "$REPO_DIR/.git" ]; then
    log "skip: $REPO_DIR is not a git repo"
    exit 0
fi

cd "$REPO_DIR"

# 节流
NOW="$(date +%s)"
if [ -f "$STAMP_FILE" ]; then
    LAST="$(cat "$STAMP_FILE" 2>/dev/null || echo 0)"
    DIFF=$((NOW - LAST))
    if [ "$DIFF" -lt "$THROTTLE_SEC" ]; then
        exit 0
    fi
fi

# 必须在 master 分支(避免在临时分支意外 pull)
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [ "$BRANCH" != "master" ]; then
    log "skip: not on master (current: $BRANCH)"
    exit 0
fi

# dirty working tree → 跳过
if ! git diff --quiet || ! git diff --cached --quiet; then
    log "skip: dirty working tree (run: cd $REPO_DIR && git status)"
    exit 0
fi

# 必须有 origin remote
if ! git remote get-url origin >/dev/null 2>&1; then
    log "skip: no origin remote configured"
    exit 0
fi

# fetch
if ! git fetch --quiet origin master 2>>"$LOG_FILE"; then
    log "skip: git fetch failed (network?)"
    exit 0
fi

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/master)"

# 已经最新
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$NOW" > "$STAMP_FILE"
    log "ok: already up to date @ ${LOCAL:0:7}"
    exit 0
fi

# 必须能 fast-forward(LOCAL 是 REMOTE 的祖先)
if ! git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
    log "skip: non-fast-forward (local has unpushed commits?)"
    exit 0
fi

# untracked 撞名预检:fast-forward 会新建 REMOTE 相对 LOCAL 的新增文件,
# 若这些路径本地已存在为 untracked 文件,git pull 会 abort。预检识别 → 跳过。
COLLISIONS=""
while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ -e "$REPO_DIR/$f" ]; then
        COLLISIONS="${COLLISIONS:+$COLLISIONS, }$f"
    fi
done < <(git diff --name-only --diff-filter=A "$LOCAL" "$REMOTE")

if [ -n "$COLLISIONS" ]; then
    log "skip: untracked files would be overwritten: $COLLISIONS"
    exit 0
fi

# pull + install
log "pulling: ${LOCAL:0:7} → ${REMOTE:0:7}"
if ! git pull --ff-only --quiet origin master >>"$LOG_FILE" 2>&1; then
    log "error: git pull failed"
    exit 0
fi

AFTER_HASH="$(git rev-parse HEAD)"

log "running install.sh"
# stdout 通常被 launchd/systemd 捕获进同一份日志,这里再 tee 一份保证独立可读
bash "$REPO_DIR/install.sh" 2>&1 | tee -a "$LOG_FILE"

INSTALL_EXIT="${PIPESTATUS[0]:-$?}"
if [ "$INSTALL_EXIT" -ne 0 ]; then
    log "error: install.sh exited $INSTALL_EXIT"
    exit 0
fi

echo "$NOW" > "$STAMP_FILE"
log "ok: updated to ${AFTER_HASH:0:7}"
