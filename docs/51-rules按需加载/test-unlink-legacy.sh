#!/usr/bin/env bash
# install.sh 中 unlink_legacy_dir 的沙盘测试。
#
# 为什么值得单独测：这个函数会 rm 掉 <agent_home>/rules，判据写错的两种后果都很贵——
#   漏删 → 老机器上旧软链还在，八份领域文档继续被 CC 当作用户级 memory 全文常驻，
#          本轮收益归零，而且命令全绿、无人察觉；
#   误删 → 删掉用户自建的真实 rules 目录。
# 按 playbooks/shell.md 的沙盘三要件写：副作用全落 mktemp 临时目录、每个用例现造环境、
# 断言取证于真实文件系统状态而非日志字符串。
#
# 跑法：bash docs/51-rules按需加载/test-unlink-legacy.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# 只取函数定义，不跑安装主流程
# shellcheck source=/dev/null
CCG_INSTALL_LIB_ONLY=1 source "${REPO_ROOT}/install.sh"
# install.sh 顶部的 set -euo pipefail 会传染进本脚本，两个都要关：
#   -e：断言失败要能继续往下统计；
#   -u：被测函数的入参个数一旦对不上，set -u 会让 bash 直接退出**整个测试脚本**——
#       表现为零输出 + 退出码 1，比一条 FAIL 难读得多（本轮改函数签名时就先撞了一次）。
set +eu

PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    printf '  \033[0;32mPASS\033[0m  %s\n' "$1"
}
ng() {
    FAIL=$((FAIL + 1))
    printf '  \033[0;31mFAIL\033[0m  %s\n' "$1"
}
check() { # check <条件求值结果 0/1> <用例描述>
    if [ "$1" = "1" ]; then ok "$2"; else ng "$2"; fi
}

# 每个用例现造一个沙盘：<sandbox>/repo 扮演本仓 checkout、<sandbox>/home 扮演 agent home。
# repo 里放上仓库标志文件，因为 unlink_legacy_dir 靠它们认亲（判断软链是否指向某个
# claude-code-global checkout），而不是比对某一个写死的路径——机器上可能有多个 checkout
# （主工作树 + 若干 worktree），旧软链指向哪一个都要认得出来。
new_sandbox() {
    local d
    d="$(mktemp -d)"
    mkdir -p "${d}/repo" "${d}/home"
    : >"${d}/repo/GLOBAL_AGENTS.md"
    : >"${d}/repo/install.sh"
    echo "$d"
}

echo "== unlink_legacy_dir 沙盘测试 =="

# ---- 用例 1：指向本仓 rules 的软链（目标仍存在）→ 应删除 ----
S="$(new_sandbox)"
mkdir -p "${S}/repo/rules"
ln -s "${S}/repo/rules" "${S}/home/rules"
unlink_legacy_dir "${S}/home/rules" >/dev/null 2>&1
if [ ! -L "${S}/home/rules" ] && [ ! -e "${S}/home/rules" ]; then R=1; else R=0; fi
check "$R" "用例 1：指向本仓 rules 的软链被删除"
# 软链被删，但被指向的真实目录必须完好（rm 不能穿透软链）
if [ -d "${S}/repo/rules" ]; then R=1; else R=0; fi
check "$R" "用例 1b：被指向的真实目录未受牵连"
rm -rf "$S"

# ---- 用例 2：用户自建的真实目录 → 必须原样保留 ----
S="$(new_sandbox)"
mkdir -p "${S}/home/rules"
echo "my own rule" >"${S}/home/rules/mine.md"
unlink_legacy_dir "${S}/home/rules" >/dev/null 2>&1
if [ -f "${S}/home/rules/mine.md" ]; then R=1; else R=0; fi
check "$R" "用例 2：用户自建的真实目录及其内容保留"
rm -rf "$S"

# ---- 用例 3：指向别处的软链 → 必须原样保留 ----
S="$(new_sandbox)"
mkdir -p "${S}/other"
ln -s "${S}/other" "${S}/home/rules"
unlink_legacy_dir "${S}/home/rules" >/dev/null 2>&1
if [ -L "${S}/home/rules" ] && [ "$(readlink "${S}/home/rules")" = "${S}/other" ]; then R=1; else R=0; fi
check "$R" "用例 3：指向别处的软链保留且目标不变"
rm -rf "$S"

# ---- 用例 4：路径不存在 → no-op 且退出码 0 ----
S="$(new_sandbox)"
unlink_legacy_dir "${S}/home/rules" >/dev/null 2>&1
RC=$?
if [ "$RC" = "0" ] && [ ! -e "${S}/home/rules" ]; then R=1; else R=0; fi
check "$R" "用例 4：路径不存在时 no-op 且退出码 0"
rm -rf "$S"

# ---- 用例 5：断链 → 应删除 ----
# 这是升级路径上的真实形态：git mv rules playbooks 之后，老机器上的旧软链就是断的。
# [ -L ] / readlink 在断链上仍然工作，而 [ -e ] / readlink -f 不然——写错就静默漏删。
S="$(new_sandbox)"
mkdir -p "${S}/repo/rules"
ln -s "${S}/repo/rules" "${S}/home/rules"
mv "${S}/repo/rules" "${S}/repo/playbooks" # 模拟 git mv，旧软链就此断掉
if [ -e "${S}/home/rules" ]; then
    ng "用例 5 前置：软链应已断掉，但 -e 仍为真，沙盘没造对"
else
    unlink_legacy_dir "${S}/home/rules" >/dev/null 2>&1
    if [ ! -L "${S}/home/rules" ]; then R=1; else R=0; fi
    check "$R" "用例 5：git mv 造成的断链被删除"
fi
rm -rf "$S"

# ---- 用例 6：软链指向「另一个 checkout」的 rules → 仍应删除 ----
# 真实场景：install 从 worktree 里跑，而旧软链指向主工作树。判据若比对当次 $REPO_DIR
# 的精确路径就会漏删——而漏删是静默的：命令全绿、八份文档继续常驻，没人会发现。
S="$(new_sandbox)"
mkdir -p "${S}/another-checkout/rules"
: >"${S}/another-checkout/GLOBAL_AGENTS.md"
: >"${S}/another-checkout/install.sh"
ln -s "${S}/another-checkout/rules" "${S}/home/rules"
unlink_legacy_dir "${S}/home/rules" >/dev/null 2>&1
if [ ! -L "${S}/home/rules" ]; then R=1; else R=0; fi
check "$R" "用例 6：指向另一个 checkout 的 rules 软链也被删除"
rm -rf "$S"

# ---- 用例 7：软链指向一个恰好叫 rules、但父目录不是本仓 checkout 的目录 → 必须保留 ----
S="$(new_sandbox)"
mkdir -p "${S}/someone-else/rules"
ln -s "${S}/someone-else/rules" "${S}/home/rules"
unlink_legacy_dir "${S}/home/rules" >/dev/null 2>&1
if [ -L "${S}/home/rules" ]; then R=1; else R=0; fi
check "$R" "用例 7：父目录无本仓标志文件时不认亲、不删"
rm -rf "$S"

# ---- 用例 8：相对路径软链 → 一律不碰 ----
# 认亲用的 [ -f "${parent}/GLOBAL_AGENTS.md" ] 在 parent 为相对路径时相对 CWD 解析，
# 而 install.sh 通常恰恰是从某个 cc-global checkout 根跑起来的——那两个标志文件就在 CWD 下，
# 于是一个内容毫不相干的相对软链会被误判成自家的而删掉。本仓自己建的软链一律是绝对路径，
# 故直接拒掉相对路径，不做花哨的解析。
S="$(new_sandbox)"
mkdir -p "${S}/home/elsewhere/rules" # 软链真正指向的地方：与本仓毫不相干
mkdir -p "${S}/repo/elsewhere"       # 陷阱：CWD 下同名目录，且带标志文件
: >"${S}/repo/elsewhere/GLOBAL_AGENTS.md"
: >"${S}/repo/elsewhere/install.sh"
ln -s "elsewhere/rules" "${S}/home/rules" # 相对软链
(
    cd "${S}/repo" || exit 1 # 模拟从 checkout 根跑 install.sh
    unlink_legacy_dir "${S}/home/rules" >/dev/null 2>&1
)
if [ -L "${S}/home/rules" ]; then R=1; else R=0; fi
check "$R" "用例 8：相对路径软链不碰（认亲只认绝对路径）"
rm -rf "$S"

echo ""
echo "通过 ${PASS}，失败 ${FAIL}"
[ "$FAIL" = "0" ]
