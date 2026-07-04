# PROMPT：轻量开发流 `/quick`

## 背景

当前的开发闭环是重量级三件套：`/start`（建 worktree + 分支 + `docs/<N>-*/` + PROMPT.md + PLAN.md 计划模式确认）→ 写代码 → `/finish`（SUMMARY.md + 跨项目沉淀反思 + 关 issue + `/devtree` + README review + `/commit` + worktree 收尾）。

`/start --no-worktree` 只砍掉了 worktree 一层，PROMPT/PLAN/SUMMARY 三件套、docs 目录、计划模式、devtree/沉淀反思等仪式**仍然全在**。对于「只改一个很小的函数」这类需求，这套流程是重型武器打苍蝇——完全不需要落 docs 文档、不需要开发树、不需要计划模式，只要在 commit message 里说清楚「改了啥、为什么」即可。

用户已考虑过「纯自由对话」路子，但它的真实缺口是：自由对话能省掉文档，但 `/commit` 的价值（lint 门禁、`[round N]` 前缀探测、semantic message + Co-authored-by trailer）还得手动调 `/commit` 才拿得到，而且自由对话没有一个「明确的收尾动作」来触发它。所以需要一个 skill 把「轻量收尾」自动化。

## 需求

新增一个**单个** skill `/quick`，提供「简易开发流」：逻辑类似 `start + finish` 的极简版，但**不落 docs、不开 worktree、不进计划模式、不做总结/沉淀/devtree**。

### 已确认的方向性决策

1. **单个 skill `/quick`**（而非一对 `/quick` + `/wrap`）：从头管到尾——直接写代码 → 自动 `/commit` 收尾。小改动一气呵成，中间无需暂停点（start/finish 拆开是因为中间要人 review PLAN，quick 没有这个暂停需求）。
2. **默认在当前分支直接改**：不建任何分支 / worktree，在当前分支直接改、直接 commit。最轻，贴合「小函数改一下」。前提是调用时本就在干净的、想改的分支上。**保留 `--branch` 开关**：按需切轻量分支 `quick/<描述>`（不建 worktree），改完 commit 留在该分支等用户手动合。
3. **可选支持关联 issue**：允许传 `#<issue>` 让 commit 带 `Closes #N`，复用已有闭环；不传就纯 commit，不强制。简易流本质是「无 issue 无追踪」场景，issue 关联是低成本顺手项、不是主线。

### 明确不做（与 `/finish` 的边界）

`/quick` **不**碰：SUMMARY.md、跨项目沉淀反思、`/devtree`、README review、issue 生命周期管理（`/finish` 那套关联并关闭 issue）、worktree 收尾（rebase/FF merge/清理）。这些都是「重流程」独有的仪式，简易流一概不引入——要这些就走正规 `/start` + `/finish`。

## 交付物

- 新增 `skills/quick/SKILL.md`
- `README.md` skills 段新增 `/quick` 一行 + 必要处点明「轻量 vs 重流程」的选择
- `install.sh` 重跑使新 skill 生效（新增 skill 目录需重装，见项目 CLAUDE.md）
- 视情况在 `GLOBAL_AGENTS.md` 的「核心开发模式」处点一句「轻量改动可用 /quick」（与现有 `--no-worktree` 提示并列）

## 约束

- 遵循项目既有 skill 的写法与审美（各司其职、拍平并列，不搞「核心详写 + 其他简列」的分层）。
- `/quick` 内部复用 `/commit`（不重复实现 lint 门禁 / commit message 规则 / Co-authored-by trailer），保持单一真源。
- `[round N]` 前缀：`/commit` 已有「非 round 分支时看 `docs/<N>-*/` 路径兜底」逻辑；`/quick` 默认既不建 round 分支也不建 docs 目录 → 天然探不出 N → 走普通 commit 不加前缀。这符合预期（简易流本就不进轮次追踪），无需特殊处理。
