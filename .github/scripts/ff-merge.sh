#!/usr/bin/env bash
# 把一个已批准的 PR 以 fast-forward 方式合入默认分支，由 .github/workflows/ff-merge.yml 调用。
#
# 语义与 /finish 的 worktree 收尾（rebase → merge --ff-only，冲突 abort 兜底）一致，
# 只是把同一套动作搬到远端：先试纯 FF，base 前进了就先 rebase 再 FF，冲突一律停手不硬合。
#
# 入参全部走环境变量（而非 workflow 的 ${{ }} 内插），使评论正文这类不可信输入
# 不可能被拼进命令行。
set -euo pipefail

PR_NUMBER=${PR_NUMBER:?缺少 PR_NUMBER}
BASE_BRANCH=${BASE_BRANCH:?缺少 BASE_BRANCH}
TRIGGER=${TRIGGER:-unknown}
COMMENT_BODY=${COMMENT_BODY:-}
LABEL=ff-merge
MAX_ATTEMPTS=3

comment() { gh pr comment "${PR_NUMBER}" --body "$1" >/dev/null; }
drop_label() { gh pr edit "${PR_NUMBER}" --remove-label "${LABEL}" >/dev/null 2>&1 || true; }
# 失败一律：留评论说清原因 + 摘掉 label（便于重新打 label 重试）。
# 每一处可能失败的 git 命令都要显式 || abort —— set -e 会让它们直接退出，
# 那样 PR 上不会有任何回执、label 还挂着，人会以为「已批准待合」而实际什么都没发生。
abort() {
  comment "$1"
  drop_label
  exit 1
}

# workflow 的 if 只能做 startsWith 粗筛，精确匹配放这里，
# 免得「/ffmpeg 怎么用」这类评论误触发。取首行第一个词，故「/ff 合并吧」照样认。
# 粗筛没过的静默退出、不留评论。
if [ "${TRIGGER}" = "issue_comment" ]; then
  # tr -d '\r' 不能省：网页端提交的**多行**评论正文是 CRLF 分隔且 webhook 原样保留，
  # 而 awk 的默认分隔符不含 CR，首行第一个词会是「/ff\r」而非「/ff」，于是静默不触发。
  first_token=$(printf '%s' "${COMMENT_BODY}" | head -n 1 | tr -d '\r' | awk '{print $1}')
  if [ "${first_token}" != "/ff" ]; then
    echo "评论首行的第一个词不是 /ff，忽略"
    exit 0
  fi
fi

meta=$(gh pr view "${PR_NUMBER}" --json state,isDraft,isCrossRepository,headRefName,headRefOid,baseRefName)
state=$(printf '%s' "${meta}" | jq -r '.state')
is_draft=$(printf '%s' "${meta}" | jq -r '.isDraft')
is_fork=$(printf '%s' "${meta}" | jq -r '.isCrossRepository')
head_ref=$(printf '%s' "${meta}" | jq -r '.headRefName')
head_sha=$(printf '%s' "${meta}" | jq -r '.headRefOid')
pr_base=$(printf '%s' "${meta}" | jq -r '.baseRefName')

# 已合 / 已关的 PR 被重复打 label 是常见误操作，静默退出即可，不必留噪音评论
if [ "${state}" != "OPEN" ]; then
  echo "PR #${PR_NUMBER} 当前状态为 ${state}，跳过"
  exit 0
fi
[ "${is_draft}" = "false" ] || abort "⛔️ 这是 draft PR，先转成 ready for review 再触发 FF 合入。"
# fork PR 在 pull_request_target 下虽然拿得到写 token，但改写他人仓库的分支不是本流程的语义；
# 且 fork 分支删不掉、rebase 也推不回去，直接判掉更诚实。
[ "${is_fork}" = "false" ] || abort "⛔️ 这是来自 fork 的 PR，本流程只处理同仓分支，请手动处理。"
[ "${pr_base}" = "${BASE_BRANCH}" ] || abort "⛔️ 本 PR 的 base 是 \`${pr_base}\` 而非 \`${BASE_BRANCH}\`，不做 FF 合入。"
[ "${head_ref}" != "${BASE_BRANCH}" ] || abort "⛔️ head 与 base 同为 \`${BASE_BRANCH}\`，拒绝操作。"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git fetch --no-tags origin \
  "+refs/heads/${BASE_BRANCH}:refs/remotes/origin/${BASE_BRANCH}" \
  "+refs/heads/${head_ref}:refs/remotes/origin/${head_ref}" \
  || abort "⛔️ 拉取分支失败，无法继续。详见 Actions 日志。"

# GITHUB_TOKEN 是 GitHub App 安装令牌，服务端**硬性拒绝**推送任何新增 / 修改
# .github/workflows/ 下文件的提交，且 permissions 块里没有可声明的 workflows scope
# （contents: write 覆盖不到）。与其让 push 到一半失败，不如提前判掉说清楚。
if git diff --name-only "$(git rev-parse "refs/remotes/origin/${BASE_BRANCH}")...${head_sha}" \
  | grep -q '^\.github/workflows/'; then
  abort "$(printf '⛔️ 本 PR 触及 `.github/workflows/`，而 Actions 的 GITHUB_TOKEN 无权推送 workflow 文件（GitHub 服务端限制，提权也绕不过）。\n\n请在本地 `git merge --ff-only` 后直推。')"
fi

remote_head=${head_sha} # 远端 PR 分支当前的 tip，做 --force-with-lease 的期望值
work_head=${head_sha}   # 待合入的提交
merged_from=""
rebase_note=""

# base 可能在「读取」与「推送」之间被别处推进（本仓的 /finish 就是本地 FF 直推 master），
# 故整段是「取最新 base → 必要时重放 → 推」的有限重试，而不是一次性判断。
for _attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
  base_sha=$(git rev-parse "refs/remotes/origin/${BASE_BRANCH}")

  if ! git merge-base --is-ancestor "${base_sha}" "${work_head}"; then
    # base 前进了：重放到最新 base 上再 FF。冲突即停手——绝不 fallback 成普通 merge
    # （那正是本流程要消灭的东西）。
    echo "${BASE_BRANCH} 已前进，先 rebase 再 FF"
    git checkout --detach "${work_head}" >/dev/null 2>&1 \
      || abort "⛔️ 无法检出 PR head，已中止。详见 Actions 日志。"
    if ! git rebase "${base_sha}"; then
      git rebase --abort || true
      abort "$(printf '⛔️ FF 合入失败：`%s` 在 review 期间前进了，把本 PR 重放到最新 `%s` 时发生冲突。\n\n请手动 rebase 后重新触发。' "${BASE_BRANCH}" "${BASE_BRANCH}")"
    fi
    work_head=$(git rev-parse HEAD)
    git push --force-with-lease="${head_ref}:${remote_head}" origin "${work_head}:refs/heads/${head_ref}" \
      || abort "⛔️ rebase 后回推 PR 分支失败（分支可能在此期间又被推送过）。请重新触发。"
    # 起点固定用 PR 的原始 head：多轮重试下 remote_head 已是中间产物，
    # 拿它当起点会让回执把「原始 → 最终」记成「中间 → 最终」，审计线索就断了
    rebase_note=$(printf '\n- ⚠️ 合并前已自动 rebase 到最新 `%s`：`%s` → `%s`（内容不变，冲突会中止而非硬合）' \
      "${BASE_BRANCH}" "${head_sha:0:7}" "${work_head:0:7}")
    remote_head=${work_head}
  fi

  # 纯 FF 推送：不带 --force，非快进会被远端直接拒绝
  if git push origin "${work_head}:refs/heads/${BASE_BRANCH}"; then
    merged_from=${base_sha}
    break
  fi

  echo "推送被拒（${BASE_BRANCH} 可能又前进了），重新取最新 base 后重试"
  git fetch --no-tags origin "+refs/heads/${BASE_BRANCH}:refs/remotes/origin/${BASE_BRANCH}" \
    || abort "⛔️ 重试时拉取 ${BASE_BRANCH} 失败，已中止。"
done

[ -n "${merged_from}" ] \
  || abort "$(printf '⛔️ 连续 %s 次 FF 推送都被拒绝（`%s` 一直在前进）。请稍后重新触发。' "${MAX_ATTEMPTS}" "${BASE_BRANCH}")"

# PR head 的提交进入默认分支后，GitHub 会把该 PR 自动标记为 merged（indirect merge）。
# 这一步是异步的，轮询确认后再删分支——没确认就删，会让 PR 落成 closed 而非 merged。
merged=no
for _ in $(seq 1 10); do
  if [ "$(gh pr view "${PR_NUMBER}" --json state --jq '.state')" = "MERGED" ]; then
    merged=yes
    break
  fi
  sleep 3
done

if [ "${merged}" = "yes" ]; then
  git push origin --delete "${head_ref}" || true
  branch_note=$(printf '\n- 已删除分支 `%s`' "${head_ref}")
else
  branch_note=$(printf '\n- ⚠️ 提交已进入 `%s`，但 GitHub 尚未把本 PR 标记为 merged；分支 `%s` 保留待查。' \
    "${BASE_BRANCH}" "${head_ref}")
fi

drop_label
comment "$(printf '✅ 已 fast-forward 合入 `%s`（无 merge commit，历史保持直线）\n\n- `%s`：`%s` → `%s`\n- 触发：%s%s%s' \
  "${BASE_BRANCH}" "${BASE_BRANCH}" "${merged_from:0:7}" "${work_head:0:7}" "${TRIGGER}" "${rebase_note}" "${branch_note}")"
