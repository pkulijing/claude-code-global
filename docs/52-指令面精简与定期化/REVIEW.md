# Round 52 · review 留痕

> ⚠ **本轮全部 commit 走的是「主会话结构化自审」，未经独立 context 把关。**
>
> 原因：本 session 被显式约束「不得调用 Agent 工具」，`/review-loop` 的首选路径
> （委派独立 context 的 review orchestrator 子 agent）不可用。按 `/review-loop`
> Step 5 的降级链 **委派 > 本端结构化自审 > 不 review（禁止）**，退到第二档，
> 并按规定显著标注。
>
> **这意味着什么**：开发对话的先入之见在场，reviewer 与作者是同一个 context，
> 「实际写的和想的不一样」这类问题最容易漏。本轮改的又几乎全是指令规则文件
> （门禁自身的规则），**人工 review 是唯一的独立视角** —— 请以 `SLIM-LEDGER.md`
> 的三列账本为主要核对对象。

自审角度沿用 `/review-loop` Step 4 的默认档三角度：① 浅层 bug 扫描；② 契约与装配
（调用点、跨文件一致性）；③ 项目规范合规。

---

## 阶段 0 · `scripts/context_budget.py` + 单测

**运行验证（闸 A）**：`python3 -m unittest discover -s docs/52-指令面精简与定期化`
41 项全绿；三个子命令在真实仓库上跑通。

| # | 角度 | finding | 置信 | 处置 |
| --- | --- | --- | ---: | --- |
| 1 | ② 契约与装配 | `check-refs` 首跑在真实仓库上报 **72 条失效引用，几乎全是误报**（`src/` `frontend/` `.vscode/` 是消费方项目的目录；`bash scheduler/uninstall.sh` 是命令；`A templates/_common/...` 是 git diff 示例输出；`rules/` 是刻意保留的历史提法）。误报会让人不再看这个检查，等于白做 —— 违反脚本自己写的「宁可漏抓，绝不误报」 | 95 | **已修**：判据从「长得像路径」改为**精确白名单**，只认精简动作真正会产出的指针形态。72 → 1 |
| 2 | ① 浅层 bug | `_paths_at_ref` 用 `fnmatch` 匹配 `skills/*/SKILL.md`，而 **`fnmatch` 的 `*` 会跨 `/`**（`skills/a/b/SKILL.md` 也匹配），新侧的 `Path.glob` 则不会。`delta` 两侧口径不一致 → 算出假的增长率，而 delta 正是 `/routine-slim` 是否动手的闸 | 85 | **已修**：改用自写的 `_glob_match`（`*` → `[^/]*`）。**防假绿已验**：旧实现 `fnmatch.fnmatch('skills/a/b/SKILL.md', 'skills/*/SKILL.md')` 返回 `True`，新测试断言 `False` → 该测试在旧实现上确为红 |
| 3 | ② 契约与装配 | 标定测试原本读**工作树**的 `GLOBAL_AGENTS.md` / `CLAUDE.md`，而本轮正要把这两个文件改小 → 测试注定在阶段 3 变红，且变的是被测内容、不是估算模型 | 90 | **已修**：标定内容钉到实测那一刻的 commit（`38d3441`），改用 `file_at_ref` 读 |
| 4 | ① 浅层 bug | check-refs 收紧后剩的唯一一条是**真的**：`CLAUDE.md` 写 `scripts/ff-merge.sh`，实际文件在 `.github/scripts/ff-merge.sh`（仓库根另有一个 `scripts/`，指向了错的地方） | 90 | **已修**：改为 `.github/scripts/ff-merge.sh` + `.github/workflows/ff-merge.yml` |
| 5 | ① 浅层 bug | 空仓库（无任何 commit）跑 `delta` 会在 `resolve_since_ref` 的兜底分支抛 `CalledProcessError` | 30 | **不阻断**：本脚本只在本仓 / 有历史的仓库里跑，低置信推测式场景，按置信闸 <80 丢弃 |

**闸 B 结论**：无遗留高置信 correctness finding。**闸 C**：无 reviewer 质疑已定前提。

## 阶段 1 · `templates/MECHANICS.md` 抽取

**运行验证（闸 A）**：本阶段改的是指令规则文件，无运行时面 → 按 `/review-loop` 6.3 判 N/A。可机械验的两条已跑：`check-refs` 无失效引用、单测 41 项全绿。

| # | 角度 | finding | 置信 | 处置 |
| --- | --- | --- | ---: | --- |
| 1 | ② 契约与装配 | 抽走机制细节后，两个 skill 必须**在真正写文件之前**读到 `MECHANICS.md`，否则等于把关键约束从流程里摘掉了 | 90 | **已处理**：两处都写明触发点（bootstrap Step 3.3「动手前先读」、sync 顶部「动手改文件前先读」），并注明 `--dry-run` / 只看骨架时不必读 |
| 2 | ② 契约与装配 | `MECHANICS.md` 落在 `templates/` 顶层，会不会被 stack 探测逻辑误当成一个 stack | 85 | **不成立**：两处探测都写的是「非下划线开头的**子目录**」，`MECHANICS.md` 是文件。已复核措辞仍在 |
| 3 | ② 契约与装配 | `~/.claude/templates/MECHANICS.md` 现在读不到 —— 软链指向**主 checkout**，本 worktree 的新文件不在其中 | 100 | **非缺陷，是 worktree 的既定行为**（同 `/start` 里「新 worktree 里 gitignored 依赖一概不存在」那条）。合入 master 后即可达，`install.sh` 无需改动（`templates/` 是目录级软链） |
| 4 | ① 浅层 bug | 两个 skill 一次砍掉 58%／59%，远超 PLAN 的参考目标，可能砍过头 | 75 | **逐条核对过**：原文 16 + 17 个信息点全部落到新 SKILL.md 或 `MECHANICS.md`，账本 `SLIM-LEDGER.md` 记了三列。真正未保留的只有一条出处链接（约束本身已保留），已在账本列明 |

**闸 B 结论**：无遗留高置信 correctness finding。

## 阶段 2 · review 链路收敛

（待填）

## 阶段 3 · 宪法三板斧

（待填）

## 阶段 4 · 逐 skill 三板斧

（待填）

## 阶段 5 · `/routine-slim`

（待填）
