#!/usr/bin/env bash
# 在沙盘 git 仓上真跑 ff-merge.sh 的三条主路径，gh 用桩替身。
#
# 存在的理由：ff-merge.sh 只在 GitHub Actions 里跑，改错了要等真合并才暴露，而那时
# 影响的是 master。跑法：bash .github/scripts/ff-merge.test.sh
set -uo pipefail

SCRIPT=${1:-"$(cd "$(dirname "$0")" && pwd)/ff-merge.sh"}
ROOT=$(mktemp -d)
PASS=0
FAIL=0

mk_gh_stub() {
  # $1 = 桩目录, $2 = head 分支, $3 = head sha
  mkdir -p "$1"
  cat >"$1/gh" <<'STUB'
#!/usr/bin/env bash
# gh 桩：pr view 返回预置 JSON，其余子命令记录后成功返回
if [ "$1" = "pr" ] && [ "$2" = "view" ]; then
  case "$*" in
    *"--json state --jq"*) printf 'MERGED\n'; exit 0 ;;
    *) cat "${GH_META_FILE}"; exit 0 ;;
  esac
fi
echo "gh $*" >>"${GH_LOG}"
exit 0
STUB
  chmod +x "$1/gh"
}

setup_repo() {
  local d=$1
  rm -rf "${d}"
  mkdir -p "${d}"
  git init --quiet --bare "${d}/origin.git"
  git clone --quiet "${d}/origin.git" "${d}/work" 2>/dev/null
  cd "${d}/work"
  git config user.email t@t; git config user.name t
  echo base >a.txt; git add a.txt; git commit --quiet -m "base"
  git branch -M master; git push --quiet -u origin master
  # PR 分支：两个提交
  git switch --quiet -c feature
  echo one >>a.txt; git commit --quiet -am "feat 1"
  echo two >>a.txt; git commit --quiet -am "feat 2"
  git push --quiet -u origin feature
  git switch --quiet master
}

# run_script <沙盘目录> [触发事件] [评论正文]
run_script() {
  local d=$1
  local trigger=${2:-pull_request_target}
  local body=${3:-}
  cd "${d}/work"
  local head_sha
  head_sha=$(git rev-parse origin/feature)
  cat >"${d}/meta.json" <<EOF
{"state":"OPEN","isDraft":false,"isCrossRepository":false,
 "headRefName":"feature","headRefOid":"${head_sha}","baseRefName":"master"}
EOF
  mk_gh_stub "${d}/bin"
  PATH="${d}/bin:${PATH}" \
    GH_META_FILE="${d}/meta.json" GH_LOG="${d}/gh.log" \
    PR_NUMBER=1 BASE_BRANCH=master TRIGGER="${trigger}" COMMENT_BODY="${body}" \
    bash "${SCRIPT}" >"${d}/out.log" 2>&1
  echo $?
}

check() {
  if [ "$2" = "$3" ]; then
    printf '  ✅ %s\n' "$1"; PASS=$((PASS + 1))
  else
    printf '  ❌ %s（期望 %s，实际 %s）\n' "$1" "$3" "$2"; FAIL=$((FAIL + 1))
  fi
}

# ---------- 用例 1：纯 FF ----------
echo "用例 1 · 纯 FF（master 未前进）"
D=${ROOT}/c1; setup_repo "${D}"
rc=$(run_script "${D}")
cd "${D}/work"; git fetch --quiet origin
check "退出码 0" "${rc}" "0"
check "master 已 FF 到 feature tip" \
  "$(git rev-parse origin/master 2>/dev/null)" "$(git rev-parse feature)"
check "master 上无 merge commit" \
  "$(git rev-list --merges origin/master | wc -l | tr -d ' ')" "0"
check "远端 feature 分支已删" \
  "$(git ls-remote --heads origin feature | wc -l | tr -d ' ')" "0"

# ---------- 用例 2：master 前进 → 先 rebase 再 FF ----------
echo "用例 2 · master 在 review 期间前进（需 rebase）"
D=${ROOT}/c2; setup_repo "${D}"
cd "${D}/work"
echo other >b.txt; git add b.txt; git commit --quiet -m "别人推的提交"
git push --quiet origin master
git reset --quiet --hard origin/master
rc=$(run_script "${D}")
cd "${D}/work"; git fetch --quiet origin
check "退出码 0" "${rc}" "0"
check "master 上无 merge commit" \
  "$(git rev-list --merges origin/master | wc -l | tr -d ' ')" "0"
check "master 含 PR 的两个提交" \
  "$(git log --format=%s origin/master | grep -c 'feat ')" "2"
check "master 含别人那个提交" \
  "$(git log --format=%s origin/master | grep -c '别人推的提交')" "1"
check "回执提到自动 rebase" \
  "$(grep -c '自动 rebase' "${D}/gh.log")" "1"

# ---------- 用例 3：PR 触及 .github/workflows/ → 提前判掉 ----------
echo "用例 3 · PR 触及 .github/workflows/（GITHUB_TOKEN 推不了）"
D=${ROOT}/c3; setup_repo "${D}"
cd "${D}/work"
git switch --quiet feature
mkdir -p .github/workflows; echo "on: push" >.github/workflows/x.yml
git add .github/workflows/x.yml; git commit --quiet -m "改 workflow"
git push --quiet origin feature; git switch --quiet master
before=$(git rev-parse origin/master)
rc=$(run_script "${D}")
cd "${D}/work"; git fetch --quiet origin
check "退出码 1（中止）" "${rc}" "1"
check "master 未被推进" "$(git rev-parse origin/master)" "${before}"
check "PR 上留了说明评论" \
  "$(grep -c 'GITHUB_TOKEN 无权推送 workflow 文件' "${D}/gh.log")" "1"
check "ff-merge label 被摘掉" \
  "$(grep -c -- '--remove-label ff-merge' "${D}/gh.log")" "1"

# ---------- 用例 4：/ff 评论触发的三种正文 ----------
# 网页端多行评论走 CRLF，首行第一个词会带 \r —— 不剥掉就会静默不触发，
# 而静默不触发正是本流程最不该有的失败方式（人以为已批准、实际什么都没发生）。
echo "用例 4 · /ff 评论触发（含 CRLF 多行与形近词）"
# comment_case <序号> <用例名> <期望 merge|skip> <评论正文>
# 正文按位置参数传，不走 IFS 打包 —— CRLF 多行正文塞不进单行 read
comment_case() {
  local idx=$1 name=$2 want=$3 body=$4 d before after rc
  d=${ROOT}/c4-${idx}
  setup_repo "${d}"
  cd "${d}/work"; before=$(git rev-parse origin/master)
  rc=$(run_script "${d}" issue_comment "${body}")
  cd "${d}/work"; git fetch --quiet origin
  after=$(git rev-parse origin/master)
  if [ "${want}" = "merge" ]; then
    check "${name} → 合入" "${rc}-$([ "${after}" != "${before}" ] && echo moved || echo same)" "0-moved"
  else
    check "${name} → 忽略且不动 master" "${rc}-$([ "${after}" = "${before}" ] && echo same || echo moved)" "0-same"
  fi
}
comment_case 1 "单行 /ff" merge "/ff"
comment_case 2 "多行 CRLF（网页端提交的形态）" merge "$(printf '/ff\r\n合并吧')"
comment_case 3 "单行带参 /ff 合并吧" merge "/ff 合并吧"
comment_case 4 "形近词 /ffmpeg 怎么用" skip "/ffmpeg 怎么用"

echo
printf '合计：%s 通过 / %s 失败\n' "${PASS}" "${FAIL}"
[ "${FAIL}" -eq 0 ]
