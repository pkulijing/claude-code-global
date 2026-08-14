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
INFLIGHT_FILE="$AGENT_HOME/.auto-update-inflight"
mkdir -p "$LOG_DIR"

# ---------- 日志辅助 ----------
ts() { date "+%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(ts)] $*" >> "$LOG_FILE"; }

# ---------- 跑 install.sh 并收尾 ----------
# 两条路径共用:① 正常 pull 之后;② 上次死在 install.sh 里、本次补跑(见下方
# FORCE_INSTALL)。install.sh 本身幂等,重复跑无副作用。本函数不返回,直接收尾退出。
run_install_and_finish() {
    log "running install.sh"
    # 只在标记不存在时写时间戳。补跑路径下标记本就还在,要保留的是**最初**那次
    # 失败的时间 —— 「已经坏了多久」正是本轮要恢复的信号(上次故障静默了四天),
    # 每次补跑都覆写成当前时间等于把它抹掉,日志会永远显示「上次坏在一小时前」。
    [ -f "$INFLIGHT_FILE" ] || echo "$NOW" > "$INFLIGHT_FILE"
    # stdout 通常被 launchd/systemd 捕获进同一份日志,这里再 tee 一份保证独立可读
    bash "$REPO_DIR/install.sh" 2>&1 | tee -a "$LOG_FILE"

    # 紧跟 pipeline 取 PIPESTATUS,中间不能插任何命令(包括 `local` 声明,
    # 它自身会把 PIPESTATUS 重置成 (0))。
    INSTALL_EXIT="${PIPESTATUS[0]:-$?}"
    if [ "$INSTALL_EXIT" -ne 0 ]; then
        # 标记**故意不清**:非零退出与被硬杀留下的是同一个洞 —— 两种情形下 pull
        # 都已成功、部署都没做完,而下次运行会因 LOCAL == REMOTE 走「已是最新」
        # 直接退出。留住标记才能触发补跑,否则机器永久停在半截部署,且日志从下次
        # 起转绿,要等上游出现新提交才被顺带修好。
        log "error: install.sh exited $INSTALL_EXIT"
        exit 0
    fi
    # 只有真正成功才清标记
    rm -f "$INFLIGHT_FILE"

    AFTER_HASH="$(git rev-parse HEAD)"
    echo "$NOW" > "$STAMP_FILE"
    log "ok: updated to ${AFTER_HASH:0:7}"
    exit 0
}

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

# ---------- 上次运行是否中途暴毙 ----------
# install.sh 跑之前落一个 in-flight 标记,**只有它成功完成才清除**。于是两种失败
# ——被硬杀、以及干净地非零退出——都会把标记留在原地,下一次运行既能把这件事说
# 出来,也能据此补跑。二者留下的是同一个洞,不该区别对待。
# 不用 trap:SIGKILL 下 trap 根本不执行,而这里要防的恰恰是被强杀
# (曾真实发生:调度器重注册 unload 掉自己所在的 job,整条链被连锅端,
#  全程零输出,潜伏两个月才被发现。详见 docs/58-调度器自杀式重注册/)。
#
# 标记还兼作**补跑闸**:上次死在 install.sh 里时,pull 往往已经成功了,于是本次
# 走「已是最新」分支直接退出 —— 部署就永远停在半截,直到下次有新提交才被顺带
# 修好。故发现残留标记时置 FORCE_INSTALL,让「已是最新」那条路也补跑一次
# install.sh(它本身幂等)。
#
# **位置刻意压到这里**(所有 skip 分支之后、真正要动手之前):放在开头的话,
# 「检测到标记 → 清掉 → 却因工作树脏 / fetch 失败而 bail」会把补跑机会静默丢掉,
# 而标记恰恰是为了根除这类静默失败。压到这里,任何提前退出都让标记原样留存,
# 阻塞一解除就自动补上。
FORCE_INSTALL=0
if [ -f "$INFLIGHT_FILE" ]; then
    PREV="$(cat "$INFLIGHT_FILE" 2>/dev/null || echo 0)"
    PREV_HUMAN="$(date -r "$PREV" "+%Y-%m-%d %H:%M:%S" 2>/dev/null \
        || date -d "@$PREV" "+%Y-%m-%d %H:%M:%S" 2>/dev/null \
        || echo "$PREV")"
    # ${} 定界不可省:$var 紧贴全角字符时,bash 会把该字符的首字节吃进变量名,
    # 配合本脚本的 set -u 就是「报告崩溃的那一行自己崩掉」。
    # 实测 bash 3.2:UTF-8 locale 下裸写 $PREV_HUMAN 报 unbound variable。
    log "warn: 上次的 install.sh 未成功完成（被中断或非零退出，${PREV_HUMAN}），本次补跑"
    FORCE_INSTALL=1
fi

# 已经最新。唯一的例外是上次死在 install.sh 里(FORCE_INSTALL),那时 pull 早已
# 完成、缺的只是部署,要落到下面把 install.sh 补跑一遍。
if [ "$LOCAL" = "$REMOTE" ]; then
    if [ "$FORCE_INSTALL" != "1" ]; then
        echo "$NOW" > "$STAMP_FILE"
        log "ok: already up to date @ ${LOCAL:0:7}"
        exit 0
    fi
    run_install_and_finish
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

run_install_and_finish
