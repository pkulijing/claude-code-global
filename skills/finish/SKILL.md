---
name: finish
description: 完成当前开发项：撰写 SUMMARY.md，反思跨项目可沉淀流程并可向 claude-code-global 提 issue，关联并关闭 issue（GitHub / GitLab，如有），提交代码
disable-model-invocation: false
---

用户调用此 skill 表示当前开发项已完成。

**参数处理**：先解析并剔除下列**收尾开关**，剩余 args 才当作用户对本次开发的额外说明（撰写 SUMMARY.md 时融入「局限性」「后续 TODO」「关键设计」等章节；无剩余则按常规总结）。

**收尾开关**（控制 Step 8，可组合；不带任何开关 = rebase + FF merge + 删 worktree + 删分支 + 删 backup tag 一站到底）：

| 调用 | 8.2 rebase + 备份 tag | 8.3 FF merge | 删 worktree / 分支 | 删 backup tag |
| --- | --- | --- | --- | --- |
| `/finish`（默认） | ✓ | ✓ | ✓ | ✓ |
| `--no-merge` / `--keep-branch` | ✓ | ✗ | ✗ | ✗ |
| `--keep-backup` | ✓ | ✓ | ✓ | ✗ |
| `--no-rebase` | ✗ | ⚠️ 仅当已可 FF | （随其它开关） | （随其它开关） |

- `--no-merge`（同义 `--keep-branch`）：rebase 让分支线性，但**不** FF merge；worktree / 分支 / backup tag 全保留。用于发包 / 外审前想先留分支等 review、或本轮想继续迭代。
- `--keep-backup`：正常合并清理，但保留 backup tag（高风险轮想多保几天兜底）。
- `--no-rebase`：跳过 8.2 与备份 tag；仅在「分支相对主分支已可 FF」时仍能 merge，否则停下提示。

开关可组合、语义叠加（`--no-merge --keep-backup` 与单 `--no-merge` 等价 —— 后者本就保留全部）。

## Step 1 · 撰写 SUMMARY.md

按宪法「总结」部分的要求，在 `docs/` 下当前开发项文件夹中撰写 `SUMMARY.md`（结合 args）。

末尾（「后续 TODO」之后）额外加一段 **「## 可沉淀项」**：反思本轮有没有**值得沉淀成跨项目资产 / 可复用流程**的经验，列出来并标注去向（判据见 Step 3）。无则写「暂无」，**不留空让人猜**。这是本地持久记录，Step 3 据此对跨项目项采取行动。

## Step 2 · 扫 SUMMARY 提示「刻意不做」项归档

需求以云端 issue 为单一真源，无本地索引文件。写完 SUMMARY 后扫「局限性」与「后续 TODO」段，问用户：

> 「上面有没有**刻意决定不做**的项要归档留痕（避免未来翻老 SUMMARY 误以为是遗漏）？」

用户给出条目 + 原因 → **归档为带 `wontfix` 的 closed issue**（与「issue 是真源」一致、可检索）。二选一：① 用户跑 `/backlog` 起 issue、三轴之外额外加 `wontfix`，建完随即 close；② 本步直接建：

```bash
python3 $HOME/.claude/scripts/platform_issue.py issue-create \
  --title "刻意不做：<一句话>" --body-file /tmp/wontfix.md \
  --label wontfix --label type:docs --label area:<Y> --label priority:P2
# 建完 close：gh issue close <N> -r "not planned"  /  glab issue close <N>
```

**要往 issue 补材料**（验证产物、实测数据、结论回写）时走 helper 的 `issue-comment --issue <N> --body-file <F>`，**不要直调 `gh issue comment`** —— 契约见 `scripts/platform_issue.md`。

body 写原因 + SUMMARY 路径。`wontfix` label 缺失先补进 `.github/labels.yml` 并 sync（**三轴 + wontfix 是硬要求，缺则 `issue-create` 整条失败**）。helper 契约见 `~/.claude/scripts/platform_issue.md`。

用户说「无」→ 跳过。

## Step 3 · 跨项目可沉淀流程反思（在任意项目都跑）

开发轮里冒出的「值得复用的重复流程」常散落对话里靠人捡、易错过抽象时机。这里主动反思，对**跨项目资产**类候选直接向 claude-code-global 跨仓库提 issue。

### 3.1 候选判据

扫本轮过程（含 Step 1 写的「可沉淀项」段），**尽量三条都满足**才算，宁缺毋滥控制噪音：**跨项目通用**（不是本项目特有逻辑）、**有具体落点**（能指明改哪个 template 字段 / 哪个 skill·hook / 宪法哪段）、**≥2 次的模式或明显通用**。

**最多保留 3 条**（按价值排序）。无候选 → 打印「本轮无可沉淀项」，结束本步。

### 3.2 去向分类

- **跨项目资产** → 跨仓库提 issue 到 claude-code-global（改共享模板，或新增 skill / hook / 写进宪法）
- **仅当前项目可复用** → 文字建议「在本项目跑 `/backlog` 起本地 issue」，本步**不**替用户 file

### 3.3 自指守卫

**当前仓库就是 claude-code-global**（`git rev-parse --show-toplevel` == `realpath "$HOME/.claude/global-repo"`）→ 跨项目候选改为建议走**本地 `/backlog`**，不 API 自 file。本步剩余跳过。

### 3.4 逐条确认（外部可见动作，不自动 file）

对每个跨项目候选**逐条**问用户：现在提 / 先放一放 / 不提。可只提其中几条；「先放一放」不阻塞 commit。

### 3.5 对确认要提的候选跨仓库 file

1. **派生目标 slug 与 platform**（不硬编码，多设备 / 改名都成立）：

   ```bash
   GLOBAL_DIR="$HOME/.claude/global-repo"
   URL=$(git -C "$GLOBAL_DIR" remote get-url origin)
   SLUG=$(printf '%s' "$URL" | sed -E 's#\.git$##; s#^git@[^:]+:##; s#^https?://[^/]+/##')
   case "$URL" in *github.com*) PLAT=github ;; *gitlab*) PLAT=gitlab ;; *) PLAT="" ;; esac
   ```

   目录不存在 / `URL` 取不到 / `PLAT` 空 → 跳过 file，提示「无法定位 claude-code-global，候选已记在 SUMMARY 可沉淀项段」，**不阻塞 finish**。

2. **选并校验三轴 label**：`type:*` + `priority:P2`（沉淀项默认排队）+ `area:*`（读 `$GLOBAL_DIR/.github/labels.yml` 选最贴的一个）。**三轴是硬要求。** 选完对**目标仓库**校验三个 label 都真实存在 —— `labels.yml` 未必已同步到远端，二者可能脱节：

   ```bash
   python3 "$HOME/.claude/scripts/platform_issue.py" --platform "$PLAT" label-list --repo "$SLUG"
   ```

   只从该列表挑；不在列表的不要硬塞（会让 `issue-create` 整条失败），改选已存在的同轴 label，或先 `label-sync-from-file` 同步后再校验。

3. **写临时 body**（`/tmp/distill-<n>.md`）：来源项目名 + 轮次 + 为什么值得沉淀 + 具体落点建议 + 末尾标注「跨项目自动沉淀 issue」。当前项目有 remote 就给回链 URL。

4. **调 helper 跨仓库提**（`--platform "$PLAT" issue-create --repo "$SLUG"` + 三轴 label + `--body-file`），成功则打印返回的 issue URL。

   **失败兜底（关键）**：helper 报错时**绝不去掉 `--label` 重试以求创建成功** —— 那正是历史上产出无 label 裸 issue 的原因。正确做法是回第 2 步重新校验 / 修正 label，带齐三轴重试；仍无法解决则停下把错误报给用户（候选已记在 SUMMARY，可手动补，不阻塞 finish）。

## Step 4 · 识别 issue 关联

读 `docs/<本轮编号>-*/PROMPT.md` 顶部有没有 `> 来自 [#<N> ...](<URL>)` 引用块（由 `/start <issue#>` 写入）。

**有** → 提取**全部** issue 号与 URL（一轮批量收多个 issue 时每个各一行），传给 `/commit` 让 message body 自然包含 `Closes #N`（不嵌 title）。合并到 default branch 时自动关 issue —— 该关键字在 GitHub 与 GitLab 默认分支均原生生效（GitLab 还支持 `Fixes` / `Resolves` / `Implements` 与 cross-project 引用），本 skill 无需平台分支处理。

**关多个 issue 时每个都要带自己的关闭关键字、各占一行**：

```
Closes #13
Closes #20
```

**绝不要**写成 `Closes #13 #20`（含逗号的 `Closes #13, #20` 同样不行）—— 关闭关键字只对**紧跟其后的第一个** issue 号生效，后面的会被当成普通引用、**不会关闭**。这是踩过的坑（一行写四个只关了第一个）。

**无 issue 关联**（自由描述分支）→ 跳过本步剩余部分。

### Step 4.5 · round 编号一致性检查

本轮若经历过 rebase / 历史整理，目标分支可能已占用本地 round 编号，导致 **docs 目录编号** 与 `/commit` 将生成的 `[round N]` 前缀脱节。commit 前逐条核对，**命中不一致则给出顺延计划、要求用户确认，绝不静默继续**：

1. `docs/<N>-...` 目录编号是否需顺延到下一个空位；
2. `docs/DEVTREE.md` 的 Epic 结构与索引是否随之顺延（本步在 Step 5 `/devtree` 之前，顺延后 `/devtree` 会据最新目录重生成）；
3. `/commit` 将生成的 `[round N]` 前缀是否与文档目录编号一致；
4. **顺延如需改写已提交的历史**（rename docs 目录 + amend/rebase）→ 明确提示「这会改写历史」，等用户确认才动手；
5. 顺延后重跑 `git log --oneline` / `git status` 确认三者编号一致再进 Step 5。

三者本就一致 → 打印一行「round 编号一致，无需顺延」直接进 Step 5。

## Step 5 · 调用 `/devtree`

更新开发树 `docs/DEVTREE.md`。

## Step 6 · README review & update

放在 commit 之前，让 README 改动跟本轮代码进同一 commit。命中触发清单则按 `references/readme-review.md` 执行（触发条件 / 不触发 / 判定数据源 / 子步全在那里）；否则打印一行「README review skipped: 本轮变更不在触发清单」并跳过。

## Step 7 · 调用 `/commit`

提交所有变更（含 SUMMARY.md / DEVTREE.md / README.md）。Step 4 识别到 issue 关联时，把 `Closes #N` 作为额外上下文传给它，**多 issue 按 Step 4 的硬规则各占一行**。

`/commit` 会**按当前执行的 Agent 选 `Co-authored-by` 身份** —— **Codex 执行 `/finish` 时同样不写 Claude 身份**，别在 finish 语境下被默认成 Claude。

## Step 8 · worktree 收尾

`/start` 默认在独立 worktree 内开一轮。本步在 `/commit` 之后自动判断是否在 worktree 内：

```bash
[ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ]
```

- **不在 worktree**（含 `--no-worktree` 轮）→ 打印一行「non-worktree round，跳过 worktree 收尾」，直接进 Step 9。
- **在 worktree** → **读 `references/worktree-finish.md`** 按其 8.1–8.5 执行（诊断 / 备份 + rebase / FF merge / 二次确认清理 / 不自动 push），各开关的跳过分支以上方对照表为准。

## Step 9 · 轻量提示

打印一行：

> 「如果 SUMMARY 里的『后续 TODO』有想真正推进的项，单独跑 `/backlog` 起 issue。SUMMARY 是回顾文档不是承诺清单，TODO 不必每条都开 issue。」
