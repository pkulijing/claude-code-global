#!/usr/bin/env bash
# 回归脚本:验证 scripts/auto-update.sh 在「untracked 文件与即将 fast-forward
# 拉入的新增同名文件相撞」时,走「跳过 + 报告原因」而非笼统的 git pull failed。
#
# 自包含、自清理:用 mktemp 造隔离的 $HOME / origin / 工作 clone,不碰真实环境。
# 用法: bash docs/19-修复Linux自动同步缺陷/verify-untracked-collision.sh

set -uo pipefail

# ---------- 定位仓库根与被测脚本 ----------
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SELF_DIR/../.." && pwd)"
TARGET_SCRIPT="$REPO_ROOT/scripts/auto-update.sh"

if [ ! -f "$TARGET_SCRIPT" ]; then
    echo "FAIL: 找不到被测脚本 $TARGET_SCRIPT"
    exit 1
fi

# ---------- 隔离沙箱 ----------
SANDBOX="$(mktemp -d)"
cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

FAKE_HOME="$SANDBOX/home"
ORIGIN="$SANDBOX/origin.git"
WORK="$SANDBOX/work"
mkdir -p "$FAKE_HOME"

export GIT_AUTHOR_NAME="verify" GIT_AUTHOR_EMAIL="verify@test"
export GIT_COMMITTER_NAME="verify" GIT_COMMITTER_EMAIL="verify@test"

# ---------- 造 origin:基础 commit + 一个新增 foo.txt 的 commit ----------
git init --quiet --bare "$ORIGIN"
SEED="$SANDBOX/seed"
git clone --quiet "$ORIGIN" "$SEED"
(
    cd "$SEED"
    git checkout --quiet -b master 2>/dev/null || git checkout --quiet master
    echo "base" > base.txt
    git add base.txt
    git commit --quiet -m "base commit"
    echo "incoming content" > foo.txt
    git add foo.txt
    git commit --quiet -m "add foo.txt"
    git push --quiet origin master
)

# ---------- 造工作 clone:回退一个 commit,使 LOCAL 落后 REMOTE 一个可 ff 的 commit ----------
git clone --quiet "$ORIGIN" "$WORK"
(
    cd "$WORK"
    git checkout --quiet master
    git reset --hard --quiet HEAD~1   # 回到 base commit,落后 REMOTE 一个 commit
)

# ---------- 制造撞名:工作目录建一个 untracked foo.txt ----------
echo "local untracked content" > "$WORK/foo.txt"

# ---------- 把被测脚本拷进工作 clone(脚本自定位 REPO_DIR 为其上两级) ----------
mkdir -p "$WORK/scripts"
cp "$TARGET_SCRIPT" "$WORK/scripts/auto-update.sh"

HEAD_BEFORE="$(git -C "$WORK" rev-parse HEAD)"

# ---------- 运行被测脚本(HOME 改写 → 隔离日志与 30min 节流时间戳) ----------
HOME="$FAKE_HOME" bash "$WORK/scripts/auto-update.sh" >/dev/null 2>&1

LOG_FILE="$FAKE_HOME/.claude/logs/auto-update.log"
HEAD_AFTER="$(git -C "$WORK" rev-parse HEAD)"

# ---------- 断言 ----------
fail() { echo "FAIL: $1"; [ -f "$LOG_FILE" ] && { echo "--- 日志 ---"; cat "$LOG_FILE"; }; exit 1; }

[ -f "$LOG_FILE" ] || fail "未生成日志文件 $LOG_FILE"

if ! grep -q "skip: untracked files would be overwritten" "$LOG_FILE"; then
    fail "日志未出现预期的「跳过」原因(撞名未被预检识别)"
fi

if [ "$HEAD_BEFORE" != "$HEAD_AFTER" ]; then
    fail "HEAD 发生变化($HEAD_BEFORE → $HEAD_AFTER),不应在撞名时 pull"
fi

echo "PASS: untracked 撞名被预检识别为「跳过」,未发生 pull"
