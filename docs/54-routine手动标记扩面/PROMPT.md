# 需求：给 `/routine-docs` 加一条人工标记通道，把可自动化的范围从「纯文档」扩到「人已背书的明确改动」

## 背景

`/routine-docs` 上线后运行良好：每周一 / 三 / 五扫本仓 open issue，把纯文档类分诊出来、合批、逐条走 `/quick` 做掉，每批一个 PR，PR 即人工审批闸。

但它**对「要不要纳入开发」过于保守**，保守来自两处硬边界：

1. **落点白名单只有文档**（`playbooks/*.md`、`GLOBAL_AGENTS.md`、`README.md`、`docs/`），明令禁止 `skills/*.md`、`install.sh`、`hooks/`、`scripts/`、`templates/`、`.github/`；
2. **模型分诊的四类排除**（需讨论 / 选型、需落 PLAN 长期追踪、正文没说清、疑似已完成）只能保守判——判错的代价不对称，于是宁可漏收。

结果是一批**本来完全够格自动做掉**的 issue 长期躺在 backlog 里：简单的 skill 修改与新建、明确的 template 增补、边界清晰的 bug 修复。这些活人来做同样是纯执行，正是该交给定时 agent 的。

## 需求

**核心思路：难度与风险自动区分不了，就让人来标记。** 由仓库主人手动给 issue 加一个标记，下一次 `/routine-docs` 运行时**强制将其纳入开发范围**——绕过保守的自动分诊，也解开落点白名单。

标记的本质是**人工背书**：把这条 issue 从「任何人都能写的不可信输入」提升为「owner 已过目并认可可自动执行」。这一步替换掉了原先由「落点只限文档」承担的安全职责，因此放宽落点的同时，必须把标记通道自身的授权校验做扎实。

### 范围

- 标记通道的载体、语法、授权校验；
- 被标记 issue 在 Step 1 分诊中的绕过规则——**哪些排除项被覆盖、哪些仍然不可绕过**；
- 落点白名单相应放宽，以及放宽后**必须保留的红线**；
- 放宽后 review 强度、PR 描述标注、与 `/routine-slim` 的边界协调；
- 相关文档同步（本仓 `CLAUDE.md`、`security-boundary.md`、必要时 `playbooks/cloud-routine.md`）。

### 不在范围

- 不改 `.github/workflows/ff-merge.yml` 及其准入闸；
- 「绝不以任何方式触发合入」这条硬安全边界不动；
- 不改变「PR 是唯一汇报出口 / 唯一人工闸口」的整体设计。

## 前置实证（写 PLAN 前已跑，结论见 PLAN §实证）

需求里「给 issue 加评论作为标记」是一个对 GitHub 行为的断言，涉及授权面，动手前已实测：

```bash
gh api repos/pkulijing/claude-code-global/issues/99/comments \
  --jq '.[] | {user: .user.login, author_association, created_at}'
# → {"author_association":"OWNER","user":"pkulijing", ...}

gh api "repos/pkulijing/claude-code-global/issues?state=open&per_page=3" \
  --jq '.[] | {number, comments, author_association}'
# → 列表接口直接带 comments 计数

grep -n "add_parser" scripts/platform_issue.py
# → 只有 detect-platform / auth-status / repo-slug / label-list / issue-create / issue-view / label-sync-from-file
#   本机 helper 无任何评论能力（issue #102 正是要补这个）
```

## 待确认项（人类拍板，不由 Agent 代决）

这三项各自会导致实质不同的实现，列为开工前的阻塞问题：

1. **标记载体**：评论 / label / 二者结合？——公开仓**任何人都能评论**，纯评论方案必须校验 `author_association == OWNER`；label 天然只有写权限者能打，且云端 MCP 读 label 的路径已在现有流程中实测跑通，读评论的工具能力则未实测。
2. **落点放宽到哪一档**：只到 `skills/` + `templates/`，还是连 `scripts/` / `hooks/` / `install.sh` 也放开？
3. **skill 是否改名**：扩面后 `routine-docs` 名不副实，改名要同步云端 routine 注册 prompt、本仓 `CLAUDE.md`、`/routine-slim` 中的多处引用。
