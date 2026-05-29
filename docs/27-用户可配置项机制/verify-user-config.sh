#!/usr/bin/env bash
# 回归脚本：验证 scripts/user-config.sh 的用户可配置项机制。
#
# 覆盖：
#   T1 缺失 → seed：配置文件被创建且含默认 GIT_INIT_DEFAULT_BRANCH=master
#   T2 已存在用户值 → 重跑 seed 绝不覆盖（用户把分支改成 main，仍为 main）
#   T3 example 新增 key → 逐 key 补缺追加，且不动已有用户值
#   T4 apply：读配置 → git config --global init.defaultBranch == 配置值
#   T5 空值 → 不写 git 配置（用户可借空值 opt-out）
#
# 自包含、自清理：mktemp 沙箱，CCG_USER_CONFIG 覆盖配置路径、GIT_CONFIG_GLOBAL
# 隔离全局 git 配置，全程不碰真实环境。
# 用法: bash docs/27-用户可配置项机制/verify-user-config.sh

set -uo pipefail

# ---------- 定位仓库根与被测库 ----------
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SELF_DIR/../.." && pwd)"
LIB="$REPO_ROOT/scripts/user-config.sh"
EXAMPLE="$REPO_ROOT/user.config.example.env"

[ -f "$LIB" ]     || { echo "FAIL: 找不到被测库 $LIB"; exit 1; }
[ -f "$EXAMPLE" ] || { echo "FAIL: 找不到 example $EXAMPLE"; exit 1; }

# ---------- 隔离沙箱 ----------
SANDBOX="$(mktemp -d)"
cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

PASS_COUNT=0
fail() { echo "FAIL: $1"; exit 1; }
ok()   { echo "ok: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }

# shellcheck disable=SC1090
source "$LIB"

# ---------- T1 缺失 → seed ----------
export CCG_USER_CONFIG="$SANDBOX/config.env"
[ -e "$CCG_USER_CONFIG" ] && fail "T1 前置：沙箱配置不应预先存在"
ccg_seed_user_config "$EXAMPLE"
[ -f "$CCG_USER_CONFIG" ] || fail "T1：seed 后配置文件未创建"
grep -q '^GIT_INIT_DEFAULT_BRANCH=master' "$CCG_USER_CONFIG" \
    || fail "T1：seed 内容缺少 GIT_INIT_DEFAULT_BRANCH=master"
ok "T1 缺失→seed：文件已创建且含默认值 master"

# ---------- T2 已存在用户值 → 重跑不覆盖 ----------
printf 'GIT_INIT_DEFAULT_BRANCH=main\n' > "$CCG_USER_CONFIG"
ccg_seed_user_config "$EXAMPLE"
val="$(ccg_read_config GIT_INIT_DEFAULT_BRANCH)"
[ "$val" = "main" ] || fail "T2：用户值 main 被覆盖成 '$val'"
ok "T2 已存在用户值：重跑 seed 不覆盖（仍为 main）"

# ---------- T3 example 新增 key → 补缺追加，不动已有用户值 ----------
EX2="$SANDBOX/example2.env"
{ cat "$EXAMPLE"; printf 'CCG_TEST_NEW_KEY=hello\n'; } > "$EX2"
ccg_seed_user_config "$EX2"
new_val="$(ccg_read_config CCG_TEST_NEW_KEY)"
[ "$new_val" = "hello" ] || fail "T3：新 key 未被补缺追加（读到 '$new_val'）"
val="$(ccg_read_config GIT_INIT_DEFAULT_BRANCH)"
[ "$val" = "main" ] || fail "T3：补缺追加破坏了已有用户值（读到 '$val'）"
ok "T3 example 新增 key：补缺追加且不动已有用户值"

# ---------- T4 apply：读配置 → git config --global init.defaultBranch ----------
command -v git >/dev/null 2>&1 || { echo "SKIP: 无 git，跳过 T4/T5"; echo "PASS: 全部 $PASS_COUNT 项通过（apply 跳过）"; exit 0; }
GC4="$SANDBOX/gitconfig_t4"
GIT_CONFIG_GLOBAL="$GC4" ccg_apply_git_default_branch
got="$(GIT_CONFIG_GLOBAL="$GC4" git config --global init.defaultBranch 2>/dev/null || true)"
[ "$got" = "main" ] || fail "T4：git 全局 init.defaultBranch 未被设为 main（实际 '$got'）"
ok "T4 apply：git config --global init.defaultBranch == main"

# ---------- T5 空值 → 不写 git 配置 ----------
printf 'GIT_INIT_DEFAULT_BRANCH=\n' > "$CCG_USER_CONFIG"
GC5="$SANDBOX/gitconfig_t5"
GIT_CONFIG_GLOBAL="$GC5" ccg_apply_git_default_branch
got2="$(GIT_CONFIG_GLOBAL="$GC5" git config --global init.defaultBranch 2>/dev/null || true)"
[ -z "$got2" ] || fail "T5：空值时不应写 git 配置，但读到 '$got2'"
ok "T5 空值：不动用户 git 配置"

echo "PASS: 全部 $PASS_COUNT 项通过"
