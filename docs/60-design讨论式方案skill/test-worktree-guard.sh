#!/usr/bin/env bash
# install.sh「拒绝在 linked worktree 内运行」守卫的沙盘测试。
#
# 为什么要守卫：install.sh 以脚本自身目录为 REPO_DIR，从 worktree 跑会把两端全局软链
# 整体改指到 worktree，worktree 一删全成死链。这个坑在多轮里反复出现，靠文档提醒防不住。
#
# 沙盘：每个用例现造临时 git 仓（只放一份 install.sh 副本 —— user-config / uv / scheduler
# 三步因文件缺失而跳过，副作用全部落在临时 HOME），断言取证于退出码与临时 HOME 的真实状态。
#
# 跑法：bash docs/60-design讨论式方案skill/test-worktree-guard.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# 只取函数定义，不跑安装主流程
# shellcheck source=/dev/null
CCG_INSTALL_LIB_ONLY=1 source "${REPO_ROOT}/install.sh"
set +eu

PASS=0
FAIL=0
check() { # check <0=通过> <用例描述>
    if [ "$1" = "0" ]; then
        PASS=$((PASS + 1)); printf '  PASS  %s\n' "$2"
    else
        FAIL=$((FAIL + 1)); printf '  FAIL  %s\n' "$2"
    fi
}

TMP="$(cd "$(mktemp -d)" && pwd -P)"  # macOS 的 /var 是软链，统一成物理路径以便与 git 输出比对
trap 'rm -rf "${TMP}"' EXIT

# 现造主仓 + 一个 linked worktree，git 身份与全局配置隔离
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
MAIN="${TMP}/main"
git init -q "${MAIN}"
cp "${REPO_ROOT}/install.sh" "${MAIN}/install.sh"
git -C "${MAIN}" add install.sh
git -C "${MAIN}" -c user.name=t -c user.email=t@t commit -qm init
git -C "${MAIN}" worktree add -q "${MAIN}/wt" -b wt
PLAIN="${TMP}/plain"
mkdir -p "${PLAIN}"

echo "== ccg_is_linked_worktree"
ccg_is_linked_worktree "${MAIN}/wt"; check $? "linked worktree 判为是"
ccg_is_linked_worktree "${MAIN}"; [ $? -ne 0 ]; check $? "主 checkout 判为否"
ccg_is_linked_worktree "${PLAIN}"; [ $? -ne 0 ]; check $? "非 git 目录判为否"
# 相对路径语境：从 worktree 子目录外部以相对路径调用也要判对
(cd "${TMP}" && ccg_is_linked_worktree "main/wt"); check $? "相对路径的 linked worktree 判为是"

echo "== 直接执行 worktree 里的 install.sh"
FAKE_HOME="${TMP}/home"
mkdir -p "${FAKE_HOME}/.claude"
out="$(HOME="${FAKE_HOME}" bash "${MAIN}/wt/install.sh" 2>&1)"
rc=$?
[ "${rc}" -ne 0 ]; check $? "退出码非 0（实际 ${rc}）"
[ -z "$(ls -A "${FAKE_HOME}/.claude")" ]; check $? "临时 HOME 的 .claude 下未产生任何文件"
printf '%s\n' "${out}" | grep -qxF "  bash ${MAIN}/install.sh"; check $? "提示信息给出主 checkout 下的正确命令"

echo ""
echo "PASS=${PASS} FAIL=${FAIL}"
[ "${FAIL}" -eq 0 ]
