---
name: finish
description: 完成当前开发项：撰写 SUMMARY.md，反思跨项目可沉淀流程并可向 claude-code-global 提 issue，关联并关闭 issue（GitHub / GitLab，如有），提交代码
disable-model-invocation: false
---

用户调用此 skill 表示当前开发项已完成。

**参数处理**：调用时可能附带参数（args）。先解析并剔除以下**收尾开关**，剩余 args 才当作用户对本次开发的额外说明（撰写 SUMMARY.md 时融入对应章节，如「局限性」「后续TODO」「关键设计」；若剔除开关后无剩余则按常规总结）。

**收尾开关**（控制 Step 8 worktree 收尾行为，可组合；默认不带任何开关 = rebase + FF merge + 删 worktree + 删分支 + 删 backup tag 一站到底）：

- `--no-merge`（同义词 `--keep-branch`）：rebase 让分支线性，但**不** FF merge 到主分支；worktree、分支、backup tag **全保留**。用于发包 / 外审前想先留分支等 review、或本轮想继续迭代的场景。
- `--keep-backup`：正常 FF merge + 清理 worktree / 分支，但**保留** backup tag（高风险轮想多保几天兜底）。
- `--no-rebase`：跳过 8.2 的 rebase（与备份 tag）；更激进的可选项，仅在「分支相对主分支已可 FF」时仍能 merge，否则停下提示用户先 rebase 或加 `--no-merge`。

各开关行为对照见 Step 8 顶部对比表。

执行以下步骤：

## Step 1：撰写 SUMMARY.md

按全局 CLAUDE.md「总结」部分的要求，在 `docs/` 下当前开发项文件夹中撰写 `SUMMARY.md`（结合参数内容）。

SUMMARY 末尾（「后续 TODO」之后）额外加一段 **「## 可沉淀项」**：反思本轮过程中有没有**值得沉淀成跨项目资产 / 可复用流程**的经验，列出来并标注去向（见 Step 3 的判定标准与去向分类）。无则写「暂无」，不留空让人猜。这是本地持久记录，Step 3 据此对跨项目项采取行动。

## Step 2：扫 SUMMARY 提示「刻意不做」项归档

需求以云端 issue 为**单一真源**，无本地索引文件。写完 SUMMARY 后，扫「局限性」与「后续 TODO」段，问用户：

> 「上面有没有**刻意决定不做**的项要归档留痕（避免未来翻老 SUMMARY 误以为是遗漏）？」

- 用户给出条目 + 原因 → 把它**归档为一个带 `wontfix` label 的 closed issue**（与「issue 是真源」一致、可检索、可按 label 过滤）。二选一：
  - 让用户跑 `/backlog` 起 issue，选完三轴后**额外加 `wontfix` label**，建完随即 close（`gh issue close <N> -r "not planned"` / `glab issue close <N>`）；
  - 或本步直接用 helper 建：`issue-create --title "刻意不做：<一句话>" --body-file /tmp/wontfix.md --label wontfix --label type:docs --label area:<Y> --label priority:P2`，body 写原因 + 引用本轮 SUMMARY 路径，建完 close。
  - 若 `wontfix` label 尚不存在于目标仓库 → 先补进 `.github/labels.yml` 并 `label-sync-from-file` 同步，再建 issue（三轴 + wontfix label 是硬要求，缺 label 会让 `issue-create` 整条失败）。
- 用户说「无」→ 跳过

## Step 3：跨项目可沉淀流程反思（在任意项目都跑）

本步的价值：每个开发轮里冒出的「值得复用的重复性流程」常散落在对话里靠人捡，容易错过抽象时机。这里主动反思，并对**跨项目资产**类候选**直接向 claude-code-global 仓库提 issue**（跨仓库），不靠人事后回忆。

**这类跨仓库 issue 独立于当前项目**——它是在 claude-code-global 仓库里发起的云端 issue（那里的 open 项由其自己的 saved query 速览），与当前项目无索引耦合。

### 3.1 反思候选 + 判定标准

扫本轮过程（含 Step 1 写的「可沉淀项」段），按标准挑候选——**尽量三条都满足**才算，宁缺毋滥控制噪音：

- **跨项目通用**：不是本项目特有逻辑；
- **有具体落点**：能指明改哪个 template 字段 / 哪个 skill·hook / GLOBAL_AGENTS.md 哪段；
- **≥2 次的模式**，或明显通用。

**最多保留 3 条**（按价值排序取 top 3）。无候选 → 打印「本轮无可沉淀项」，结束本步。

### 3.2 候选去向分类

- **跨项目资产** → 跨仓库提 issue 到 claude-code-global：
  1. 改 `~/.claude/templates/` 下的共享模板；
  2. 在 claude-code-global 里新增 skill / hook / 写进 `GLOBAL_AGENTS.md`。
- **仅当前项目可复用** → 文字建议「在本项目跑 `/backlog` 起本地 issue」，本步**不**替用户 file。

### 3.3 自指守卫

若**当前仓库就是 claude-code-global**（`git rev-parse --show-toplevel` == `realpath "$HOME/.claude/global-repo"`）→ 跨项目资产候选改为建议走**本地 `/backlog`**（遵循本项目「issue 即单一真源」约定），不 API 自 file。本步剩余跳过。

### 3.4 逐条确认（外部可见动作，不自动 file）

对每个跨项目候选，**逐条**用 AskUserQuestion 问用户：现在提 / 先放一放 / 不提。逐条决策、可只提其中几条；「先放一放」不阻塞 commit。

### 3.5 对确认要提的候选，跨仓库 file

1. **派生目标 slug + platform**（不硬编码，多设备/改名都成立；`install.sh` 把本仓库软链为 `~/.claude/global-repo`）：

   ```bash
   GLOBAL_DIR="$HOME/.claude/global-repo"
   URL=$(git -C "$GLOBAL_DIR" remote get-url origin)
   SLUG=$(printf '%s' "$URL" | sed -E 's#\.git$##; s#^git@[^:]+:##; s#^https?://[^/]+/##')
   case "$URL" in *github.com*) PLAT=github ;; *gitlab*) PLAT=gitlab ;; *) PLAT="" ;; esac
   ```

   `$GLOBAL_DIR` 不存在 / `URL` 取不到 / `PLAT` 空 → 跳过 file，提示「无法定位 claude-code-global，候选已记在 SUMMARY 可沉淀项段，可手动提 issue」，不阻塞 finish。

2. **选并校验三轴 label**：`type:*`（按性质取 feat/refactor/docs）+ `priority:P2`（默认排队，沉淀项少有紧急）+ `area:*`——读 `$GLOBAL_DIR/.github/labels.yml` 在 install/skill/hook/template/doc 里选最贴的一个。

   **三轴 label 是硬要求**（helper 已对跨仓库零-label 创建强制拦截）。选完务必对**目标仓库**校验三个 label 都真实存在（labels.yml 是真源、未必已同步到远端，二者可能脱节）：

   ```bash
   python3 "$HOME/.claude/scripts/platform_issue.py" --platform "$PLAT" label-list --repo "$SLUG"
   ```

   只从该列表里挑 label。若选中的 label 不在列表中 → 不要硬塞（会让下一步 `issue-create` 整条失败），改选已存在的同轴 label，或先 `label-sync-from-file "$GLOBAL_DIR/.github/labels.yml"` 把 labels.yml 同步到远端后再校验。

3. **写临时 body**（`/tmp/distill-<n>.md`）：来源项目名 + 轮次 + 为什么值得沉淀（重复性/通用性）+ 具体落点建议 + 末尾标注「跨项目自动沉淀 issue」。当前项目有 remote 就给回链 URL，否则写项目目录名。

4. **调 helper 跨仓库提**：

   ```bash
   python3 "$HOME/.claude/scripts/platform_issue.py" --platform "$PLAT" \
     issue-create --repo "$SLUG" \
     --title "<标题>" --body-file /tmp/distill-<n>.md \
     --label type:<X> --label area:<Y> --label priority:P2
   ```

   成功则打印返回的 issue URL 给用户。

   **失败兜底（关键）**：若 helper 报错（如某 label 在目标仓库不存在导致 `gh`/`glab` 整条失败），**绝不去掉 `--label` 重试以求创建成功**——那正是历史上产出无 label 裸 issue（如 #12）的原因。正确做法：按 step 2 重新校验/修正 label（改选已存在的，或先 `label-sync-from-file`），带齐三轴重试；若仍无法解决，停下把错误报给用户，候选已记在 SUMMARY 可沉淀项段、可手动补，不阻塞 finish。

## Step 4：识别 issue 关联

读 `docs/<本轮编号>-*/PROMPT.md` 顶部，看是否有 `> 来自 [#<N> ...](<URL>)` 引用块（由 `/start <issue#>` 写入）：

- **有 issue 关联** → 提取**全部** issue 号 `#N` 与 URL（PROMPT.md 顶部可能有多个引用块——一轮批量收多个 issue 时每个 issue 各一行），记下用于后续：
  - 让 `/commit` 在 message body 写 `Closes #N`，commit/PR 合并到 default branch 时**自动关 issue** —— 该关键字在 GitHub 与 GitLab 默认分支均原生生效（GitLab 还支持 `Fixes` / `Resolves` / `Implements` 等更多关键词与 cross-project `Closes group/project#N` 引用），本 SKILL 不需要平台分支处理
  - **关多个 issue 时：每个 issue 都要带自己的关闭关键字，各占一行**：

    ```
    Closes #13
    Closes #20
    Closes #23
    ```

    **绝不要**写成 `Closes #13 #20 #23`（含逗号的 `Closes #13, #20` 同样不行）—— GitHub / GitLab 的关闭关键字只对**紧跟其后的第一个** issue 号生效，后面的号会被当成普通引用、**不会关闭**。这是踩过的坑（一行写四个只关了第一个），务必逐个带关键字。

    issue 关闭由 `Closes #N` 合并时自动完成，无本地索引需清理（需求以云端 issue 为单一真源）。

- **无 issue 关联**（自由描述分支） → 仅按本步骤剩余动作走，不涉及 issue 关联

## Step 5：调用 `/devtree`

调用 `/devtree` 更新开发树（`docs/DEVTREE.md`）。

## Step 6：README review & update

仅当本轮变更命中下述触发清单才进入此步；否则打印一行「README review skipped: 本轮变更不在触发清单」并跳过。

放在 commit 之前是为了让 README 改动跟本轮代码进同一 commit。

### 触发条件清单

满足任一即触发：

1. **skill 增减**：`skills/<name>/` 子目录新增或删除
2. **hook 增减**：`hooks/*` 文件新增或删除
3. **顶层目录结构变化**：仓库根目录、`skills/` / `templates/` / `hooks/` 这几层出现新增 / 删除子目录
4. **面向用户的工作流改动**：本轮 PROMPT.md 或 SUMMARY.md 中明示「面向用户的入口/约定改了」（例：需求管理 / issue 驱动、安装方式、模板使用方式、命令行接口）

明示**不触发**：

- 纯内部重构（重命名变量、抽函数、调整文件分割）
- bug fix
- 仅改 `docs/` 下的开发记录
- 依赖升级

### 判定数据源

- `git status --porcelain` + `git diff --cached --name-status` 的并集（本步在 commit 前跑，未提交变更也要算）
- **明示忽略**前面几步刚改的 `SUMMARY.md` / `DEVTREE.md` 自身 —— 它们不应触发 README review

### 触发后子步

1. 读 `README.md` + 本轮 `PROMPT.md` / `SUMMARY.md`
2. 列出 README 中需要新增 / 修改的具体段落（**只动相关段落，不重写整篇**）
3. 直接 Edit `README.md`
4. 一句话告知用户改了什么（例：「README 已更新：在 Skills 段新增 `/foo` 一节」）

## Step 7：调用 `/commit`

调用 `/commit` 提交所有变更（包括 SUMMARY.md / DEVTREE.md / README.md 的变化）。

`/commit` 会**按当前执行的 Agent 选择 `Co-authored-by` 身份**（CC → Claude、Codex → OpenAI Codex，详见 `/commit` 第 8 步与全局 CLAUDE.md「git 规则」）—— **Codex 执行 `/finish` 收尾时同样不写 Claude 身份**，不要在 finish 语境下被默认成 Claude。

**关键**：如果 Step 4 识别到 issue 关联，把 `Closes #N` 作为额外上下文传给 commit skill —— 让生成的 commit message body 自然包含 `Closes #N`（不要嵌入 title）。GitHub / GitLab 均原生识别此关键字，无需平台分支。**关多个 issue 时务必每个 issue 各一行、各带关键字**（`Closes #13` / `Closes #20` / …），**不能**一行写 `Closes #13 #20`（只会关第一个，见 Step 4 的硬规则）。

## Step 8：worktree 收尾

`/start` 默认在独立 worktree 内开一轮（见 `/start` skill）。本步在 `/commit` 之后自动判断是否在 worktree 内，是则一站式完成「rebase → FF merge → 清理」，免去手工三步走。

**先检测是否在 linked worktree 内**：

```bash
[ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ]
```

- **不在 worktree**（两者相等，含 `--no-worktree` round）→ 打印一行「non-worktree round，跳过 worktree 收尾」，直接进 Step 9。
- **在 worktree** → 按下方**收尾开关对照表**决定流程。

**收尾开关对照表**（开关来自 ARGUMENTS 解析，✓=执行 / ✗=跳过保留）：

| 调用                           | 8.2 rebase + 备份 tag | 8.3 FF merge   | 8.4 删 worktree | 8.4 删分支     | 8.4 删 backup tag |
| ------------------------------ | --------------------- | -------------- | --------------- | -------------- | ----------------- |
| `/finish`（默认）              | ✓                     | ✓              | ✓               | ✓              | ✓                 |
| `--no-merge` / `--keep-branch` | ✓                     | ✗              | ✗               | ✗              | ✗（保留）         |
| `--keep-backup`                | ✓                     | ✓              | ✓               | ✓              | ✗（保留）         |
| `--no-rebase`                  | ✗                     | ⚠️ 仅当已可 FF | （随其它开关）  | （随其它开关） | （随其它开关）    |

开关可组合，语义叠加（如 `--no-merge --keep-backup` 与单 `--no-merge` 等价——后者本就保留全部）。各分支的具体动作见 8.3 / 8.4。

收尾流程遵循 `/rebase` skill 的核心原则（FF-only、备份 tag、冲突逐文件解、abort 兜底、分段确认），但**不调用 `/rebase` skill** —— 因 `/rebase` 阶段 3 的 `git checkout <主分支>` 在 worktree 下必失败（主分支已被主工作树占用），FF merge 须改用 `git -C <主工作树> merge`。

### 8.1 诊断

展示 `git worktree list`、`git branch --show-current`、`git status`（应干净，`/commit` 刚跑完）、`git log --graph --oneline -15`。

**探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（得 `origin/master` → 取末段）；失败则本地探测 `main` / `master`。

**算主工作树路径**：`dirname "$(git rev-parse --path-format=absolute --git-common-dir)"`。

前置检查：当前分支不能就是主分支；工作区必须干净。任一不满足 → 停下问用户。

### 8.2 备份 + rebase

> **`--no-rebase`**：跳过本整节（不打备份 tag、不 rebase），直接进 8.3。后续 8.3 仅在分支相对主分支「已可 FF」时才合并，否则停下提示。

1. **备份 tag**：`git tag backup/<分支名>-$(date +%Y%m%d-%H%M)`，告诉用户「搞砸了用 `git reset --hard <该 tag>` 回退」。
2. **rebase**：`git rebase <主分支>`。
   - **无冲突** → 展示 `git log --graph --oneline -10`，停下等用户确认后进 8.3。
   - **有冲突**（finish 跑过 `/devtree`，`DEVTREE.md` 几乎必与主分支并行进度撞车）→ `git status` 列冲突文件，**逐个解、逐个 `git add`**，再 `git rebase --continue`；后续 commit 续冲突则重复。**冲突时暂停让用户解，不自动跳过**；随时可 `git rebase --abort` + 备份 tag 兜底。解完展示 graph，停下等用户确认。

### 8.3 FF merge 到主分支

> **`--no-merge` / `--keep-branch`**：跳过本节与 8.4，改走 **8.4-skip**（见下），把 worktree / 分支 / backup tag 全保留并打印其位置。

主分支 checkout 在主工作树，当前 worktree 不能 `git checkout` 它，故用 `-C` 在主工作树内合并：

```bash
git -C <主工作树> merge --ff-only <当前分支>
```

若 `--ff-only` 失败（主分支在本轮期间又前进）→ 回到 8.2 把当前分支继续 rebase 到最新主分支，再重试（`--no-rebase` 下不能自动 rebase → 停下提示用户去掉 `--no-rebase` 重跑或手动 rebase）。**禁止 fallback 普通 merge。**

### 8.4 二次确认 + 清理

向用户**明确列出**将删除的项，等用户确认（销毁性动作）。**`--keep-backup` 时** backup tag 不在删除列表里、保留。

- **用户确认** → 先 `cd <主工作树>`（当前 cwd 即将随 worktree 一起消失），再依次执行：

  ```bash
  git worktree remove <当前 worktree 路径>
  git branch -d <当前分支>
  git tag -d backup/<分支名>-<时间戳>   # --keep-backup 时跳过此行，末尾打印保留的 tag 名
  ```

  若 `git worktree remove` 失败（IDE / 编辑器占用 worktree 内文件）→ 给清晰提示「请关闭打开该目录的编辑器后重试」，**不加 `--force` 硬删**，保留全部状态。

- **用户拒绝** → 保留 worktree / 分支 / backup tag 全部状态，打印当前状态，结束。

### 8.4-skip（`--no-merge` / `--keep-branch` 专用）

不 merge、不删除任何东西。打印三项的保留位置供用户后续手动处理：

```
本轮已 commit + SUMMARY 就位，按 --no-merge 保留：
  worktree : <当前 worktree 路径>
  分支     : <当前分支>（已 rebase 到 <主分支>，线性可后续 FF）
  backup   : backup/<分支名>-<时间戳>
后续可：① 让人 review / 提 PR；② 继续在此 worktree 迭代；③ 准备好后手动 git -C <主工作树> merge --ff-only <当前分支> 并清理。
```

然后直接进 Step 9（跳过 8.5 的 push 提示——主分支未前进）。

### 8.5 不自动 push

打印一行提示：主分支已 FF 前进，是否 `git push` 由用户决定（与 finish 不自动 push 的约定一致）。

## Step 9：轻量提示

收尾打印一行：

> 「如果 SUMMARY 里的「后续 TODO」有想真正推进的项，单独跑 `/backlog` 起 issue。SUMMARY 是回顾文档不是承诺清单，TODO 不必每条都开 issue。」
