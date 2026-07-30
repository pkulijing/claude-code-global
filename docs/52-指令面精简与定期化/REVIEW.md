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

**运行验证（闸 A）**：指令规则文件，无运行时面 → N/A。`check-refs` 无失效引用；单测 41 项全绿。**另有一层真实的 dogfood**：本 commit 之后的每一次提交都在用被精简的 `/commit` 与 `/review-loop` 自身 —— 改坏了当轮就提交不了。

| # | 角度 | finding | 置信 | 处置 |
| --- | --- | --- | ---: | --- |
| 1 | ② 契约与装配 | `commit` 第 4 步删掉复述后，「2 轮未收敛的标注行必须写进 message body」这条**跨 skill 的接力**会不会断 —— 它是遗留问题在 `/finish` 前唯一的可见性 | 85 | **已处理**：这一条不属于「复述」而属于「`commit` 确实需要知道的接口」，显式保留在第 4 步，且第 7 步原有的「不得省略」措辞未动 |
| 2 | ① 浅层 bug | frontmatter description 从 380 砍到 135 字符，会不会让模型判断不出何时该调用 | 80 | **可接受**：description 的职责是回答「什么时候该调我」，新版保留了「提交前」「自动 review 迭代环」「由 /commit 自动调用，也可手动跑」三个判断要素。且本 skill 的主调用方是 `/commit` 的显式指令，不依赖模型自主发现 |
| 3 | ③ 项目规范合规 | 删掉「`description` 与 `prompt` 是 Agent 工具必填字段」是否属于删了硬约束 | 85 | **不属于**：这是工具 schema 自带的信息（漏填直接校验失败、有报错），且同一节紧接着就写着「别照抄记忆里的字段清单，schema 随版本漂移」—— 硬编码字段名与那句自相矛盾，删掉反而消除了 blog 说的 conflicting guidance |

**闸 B 结论**：无遗留高置信 correctness finding。

## 阶段 3 · 宪法三板斧

**运行验证（闸 A）**：指令规则文件，无运行时面 → N/A。`check-refs` 无失效引用；单测 41 项全绿。

| # | 角度 | finding | 置信 | 处置 |
| --- | --- | --- | ---: | --- |
| 1 | ② 契约与装配 | 别的 skill 按**章节名**引用宪法（`finish` 引「总结」部分、`commit` 引「git 规则」、`review-loop` 引 TDD 章、`sync-project-config` 引「需求管理」章）。改标题会让这些指针失效，而这类失效 `check-refs` 抓不到（它只查文件路径，不查章节锚点） | 90 | **已逐条核对**：「需求管理」「测试先行（TDD）」「git 规则」三个二级 / 三级标题原样保留；「总结」由独立小标题变为 `**总结**（Agent 主导）` 行内加粗，`finish` 的「按全局 CLAUDE.md『总结』部分的要求」仍能定位。**这是本轮 `check-refs` 覆盖不到的一类风险，已记入 SUMMARY 的局限性** |
| 2 | ① 浅层 bug | 触发条件由项目符号列表改为表格，会不会丢掉某个 playbook 或某条触发词 | 85 | **已逐条比对**：8 份 playbook 全在，触发词逐条对照原文无遗漏。`cloud-routine` 与 `scheduled-agent` 的「云端 / 本机」分野也保留在触发条件里 |
| 3 | ③ 项目规范合规 | 宪法自己写着「指令规则文件绝不自动跳过 review」，本 commit 改的就是宪法本身 | 100 | **未跳过**：本表即 review 记录，虽为降级档（主会话自审）但按规定执行并标注 |
| 4 | ① 浅层 bug | -36% 未达 PLAN 的参考目标 ~5,500（-45%） | 20 | **不阻断**：参考目标写明「不是配额，绝不为达标而删」。继续压只能动禁止删除清单里的内容 |

**闸 B 结论**：无遗留高置信 correctness finding。

## 阶段 4 · 逐 skill 三板斧 + 拆 references

**运行验证（闸 A）**：指令规则文件，无运行时面 → N/A。`check-refs` 无失效引用（含两条新的 `references/*.md` 指针）；单测 41 项全绿。

| # | 角度 | finding | 置信 | 处置 |
| --- | --- | --- | ---: | --- |
| 1 | ② 契约与装配 | **把安全推导从 `/routine-docs` 移进 reference，会不会让 agent 少了「不越线」的心理约束** —— 这是本仓最重要的一段 WHY，它防的是模型给自己找理由绕过硬规则 | 90 | **按「规则留原地、推导才移走」处理**：`--- 明确不做 ---` 一节的四条禁令、Step 0.5 的两道准入判据、`--dry-run` 零副作用全部原地未动，且各附一句压缩版理由（`sender == owner` 区分不了人和 agent；`issue_comment.created` 是订阅事件之一）。Step 0.5 顶部另加了一条**读 reference 的硬触发**（「本步要读 PR diff，动手前先读 security-boundary.md」） |
| 2 | ② 契约与装配 | `/rebase` 的 round 编号检查改成指向 `/finish` Step 4.5，但 `/rebase` 可以独立于 `/finish` 被调用 —— 指针会不会落空 | 80 | **可接受**：`/rebase` 保留了触发条件、三处脱节的对象、以及「绝不静默继续」这条判断原则，独立跑也够用；五步操作细则才需要跳转。二者同为全局 skill、路径稳定 |
| 3 | ① 浅层 bug | `/finish` Step 8 拆走后，各开关（`--no-merge` / `--keep-backup` / `--no-rebase`）的跳过分支散落在两个文件，可能对不上 | 85 | **已处理**：SKILL.md 顶部保留完整开关对照表（含 8.2/8.3/清理三列），reference 内每节开头再标一次该开关的跳过语义，两处一致。逐条比对过原文表格无出入 |
| 4 | ③ 项目规范合规 | 本轮只做了 3 个 skill，`devtree` / `start` / `quick` / `backlog` / `pybump` / `paper-read` 未动 | 40 | **有意为之**：这几个没有跨文件重复这个大头，收益主要在 A2/A3；与人类「playbooks 交给 routine 逐周做」的决定同构，正好作 routine 的首批试验场。已在账本与 SUMMARY 显式列出，**不是静默漏掉** |

**闸 B 结论**：无遗留高置信 correctness finding。

## 阶段 5 · `/routine-slim`

**运行验证（闸 A）**：新增的是指令规则文件，无运行时面 → N/A。`check-refs` 无失效引用；单测 41 项全绿。`install.sh` 兼容性**经代码核实**（`skills/*/` 逐目录 glob 收 `routine-slim/`；`scripts/*` 逐文件 glob 收 `context_budget.py`，且 `*` 不匹配 dotfile 故 `scripts/.gitignore` 不会被软链进 agent 端）——**未实跑 install.sh**，理由见下表 #4。

| # | 角度 | finding | 置信 | 处置 |
| --- | --- | --- | ---: | --- |
| 1 | ② 契约与装配 | **两条 routine 会撞车**：`/routine-docs` 每天跑、写 `playbooks/*.md`，`/routine-slim` 也写 `playbooks/*.md`。PR 可能在人手上挂好几天，**光靠 cron 时间错开根本不够** —— 两条 routine 改同一个文件必然冲突，而冲突要人来解，正是本流程要避免的 | 90 | **已加硬闸**：Step 2.2 强制列出所有 open PR、取其改动文件并集整体排除；**列不出 open PR 就中止本次运行**。这是继承 `/routine-docs` 幂等机制的同一条纪律（宁可这周不跑，也不制造必然冲突的 PR） |
| 2 | ③ 项目规范合规 | `/routine-docs` 明令禁止改 `skills/*.md`，而本 routine 的主业就是改它 —— 两条 routine 的规则直接矛盾，不解释清楚就是 blog 说的 conflicting guidance | 85 | **已写明实质理由**：二者输入不同。`/routine-docs` 把**外部 issue 正文**变成文件内容（prompt-injection 面），本 routine 只读仓库自身、不读外部文本、只做删除与搬移不引入新语义。**这是可以放宽的实质理由，不是惯例** —— 措辞已写进 Step 2.1，`CLAUDE.md` 的安全边界段也同步说明 |
| 3 | ① 浅层 bug | 本 routine 能改 `skills/`，若不显式排除自己，就能在改自身时让门禁失效 | 100 | **已硬钉黑名单**：`skills/routine-slim/**`、`skills/routine-docs/**`、`.github/**`、`install.sh`、`scripts/**`、`hooks/**`、`templates/**`、`docs/**`；并写明「**不因为『只是精简、不改语义』而放宽——判断有没有改语义的正是它自己**」 |
| 4 | ② 契约与装配 | 未实跑 `bash install.sh` 验证新 skill / 新 script 落链 | 70 | **有意不跑**：`install.sh` 从 `REPO_DIR`（= 脚本所在目录）派生软链目标，在本 worktree 里跑会把用户的 `~/.claude` / `~/.codex` **整体重指到一个未合入的分支上**，而本轮按用户要求是「提 PR 不合入」+ 事后删 worktree —— 那会留下一堆悬空软链。改为代码核实两个 glob，并把「合入后需重跑 `bash install.sh`」写进 SUMMARY 的交付说明 |
| 5 | ① 浅层 bug | 阈值 15% 与「一次只动 1–3 个文件」都是拍的，没有实证 | 45 | **不阻断，但已标注**：`--dry-run` 是上线前的硬要求（`playbooks/cloud-routine.md` §5），首次 dry-run 就是用来校准这两个数的。已写进 SUMMARY 的局限性与后续 TODO |
| 6 | ② 契约与装配 | 本 routine 不能改 `templates/`，而阶段 1 刚把 `MECHANICS.md` 放在那里 —— 这份 5,478 字符的文档从此不在自动精简的覆盖面内 | 80 | **已知缺口，有意接受**：`templates/` 整体在黑名单里是因为它承载的是**会被真实执行的项目配置**（CI、pre-commit、`pyproject.toml` 片段），放开一个文件就要在剧本里维护例外。已记入 SUMMARY 的局限性 |

**闸 B 结论**：无遗留高置信 correctness finding。
