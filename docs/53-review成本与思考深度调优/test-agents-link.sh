#!/usr/bin/env bash
# deploy_agent 的 agents/ 链接行为测试。
#
# 为什么不直接跑 install.sh：REPO_DIR 取脚本自身目录，在 worktree 里跑会把两端的
# 全部软链指向 worktree，worktree 一删就全成死链。故沿用 docs/51 的先例，用
# CCG_INSTALL_LIB_ONLY=1 只 source 出函数定义，在临时 HOME 里单测那一个函数。
#
# 用法: bash docs/53-review成本与思考深度调优/test-agents-link.sh
set -uo pipefail

MY_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FAILED=0

pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILED=1; }

# 只取函数定义，不跑安装主流程
# shellcheck disable=SC1090
CCG_INSTALL_LIB_ONLY=1 source "$MY_REPO/install.sh"

# install.sh 里 REPO_DIR="$(cd "$(dirname "$0")" && pwd)"，而 source 语境下 $0 是
# **本测试脚本**——于是 REPO_DIR 被算成 docs/53-*/ 而非仓库根。deploy_agent 读的是
# 这个全局变量，不抢回来就会去链一个不存在的 docs/53-*/agents。
REPO_DIR="$MY_REPO"

# deploy_agent 的 config_kind 分支要么要 jq（json）、要么要改 config.toml（toml）；
# 本测试只关心第 5 参的语义，故统一走 toml 分支——它对缺失的 config.toml 只 warn。
# 「config_kind 与 link_agents 正交」正是把它们拆成两个参数的理由。
run_case() {
    local name="$1" link_agents="$2"
    local tmphome
    tmphome="$(mktemp -d)"
    mkdir -p "$tmphome/.claude"
    deploy_agent "$tmphome/.claude" "CLAUDE.md" "$name" "toml" "$link_agents" >/dev/null 2>&1
    echo "$tmphome/.claude"
}

echo "== case 1: link_agents=yes → 建立指向仓库 agents/ 的软链 =="
HOME1="$(run_case "case1" "yes")"
if [ -L "$HOME1/agents" ]; then
    pass "agents 是软链"
    if [ "$(readlink "$HOME1/agents")" = "$MY_REPO/agents" ]; then
        pass "指向 $MY_REPO/agents"
    else
        fail "指向错了: $(readlink "$HOME1/agents")"
    fi
    # 目录级软链的意义：新增 .md 不重跑 install 也可见
    if [ -f "$HOME1/agents/code-reviewer.md" ]; then
        pass "经软链可读到 code-reviewer.md"
    else
        fail "经软链读不到 code-reviewer.md"
    fi
else
    fail "agents 不是软链（或不存在）"
fi
rm -rf "$(dirname "$HOME1")"

echo "== case 2: link_agents=no → 完全不建 agents（Codex 端没有这个概念）=="
HOME2="$(run_case "case2" "no")"
if [ -e "$HOME2/agents" ] || [ -L "$HOME2/agents" ]; then
    fail "不该存在 agents，却存在了"
else
    pass "未建立 agents"
fi
rm -rf "$(dirname "$HOME2")"

echo "== case 3: 省略第 5 参 → 默认不链（新参数不得改变旧调用的行为）=="
TMP3="$(mktemp -d)"
mkdir -p "$TMP3/.claude"
deploy_agent "$TMP3/.claude" "CLAUDE.md" "case3" "toml" >/dev/null 2>&1
if [ -e "$TMP3/.claude/agents" ] || [ -L "$TMP3/.claude/agents" ]; then
    fail "省略第 5 参时不该建 agents"
else
    pass "省略第 5 参时未建 agents"
fi
rm -rf "$TMP3"

echo "== case 4: 调用点接线正确（函数对了但接错线，等于没做）=="
if grep -q '^    deploy_agent "\$HOME/\.claude" "CLAUDE\.md" "Claude Code" "json" "yes"$' "$MY_REPO/install.sh"; then
    pass "CC 端传 yes"
else
    fail "CC 端调用点没传 yes"
fi
if grep -q '^    deploy_agent "\$HOME/\.codex" "AGENTS\.md" "Codex" "toml" "no"$' "$MY_REPO/install.sh"; then
    pass "Codex 端传 no"
else
    fail "Codex 端调用点没传 no"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "全部通过 ✅"
else
    echo "有用例失败 ❌"
fi
exit "$FAILED"
