# SUMMARY：轻量开发流 `/quick`

## 开发项背景

现有开发闭环是重量级三件套：`/start`（建 worktree + 分支 + `docs/<N>-*/` + PROMPT.md + PLAN.md 计划模式确认）→ 写代码 → `/finish`（SUMMARY.md + 跨项目沉淀反思 + 关 issue + `/devtree` + README review + `/commit` + worktree 收尾）。

`/start --no-worktree` 只砍掉 worktree 一层，PROMPT/PLAN/SUMMARY 三件套、docs 目录、计划模式等仪式仍全在。对「只改一个很小的函数」这类需求是重型武器打苍蝇——完全不需要落 docs、不需要计划模式，只要在 commit message 里说清楚「改了啥、为什么」即可。

用户希望一个「简易开发流」，逻辑类似 start + finish 的极简版，但不落 docs、不开发树。并明确：纯自由对话虽能省文档，但 `/commit` 的价值（lint 门禁、semantic message、Co-authored-by trailer）还得手动调，且缺一个「明确的收尾动作」触发它——所以需要 skill 做更强自动化。

## 实现方案

### 关键设计

1. **单个 skill `/quick`，而非一对 `/quick` + `/wrap`**：`/quick` 从头管到尾（直接干 → 自动 `/commit` 收尾）。start/finish 拆两截是因为中间要人 review PLAN；quick 没有这个暂停需求，一气呵成反而少一次手动调用。

2. **三档开发流谱系**：`/quick` 补齐最轻一档，形成「按需求重量选流程」的清晰谱系——

   | 档  | 入口                             | worktree | docs 三件套 | 计划模式 | 收尾仪式                                           |
   | --- | -------------------------------- | -------- | ----------- | -------- | -------------------------------------------------- |
   | 重  | `/start`→`/finish`               | ✓        | ✓           | ✓        | 全套（devtree/沉淀/README/关 issue/worktree 收尾） |
   | 中  | `/start --no-worktree`→`/finish` | ✗        | ✓           | ✓        | 全套（跳 worktree 收尾）                           |
   | 轻  | `/quick`                         | ✗        | 无          | 无       | 仅 `/commit`                                       |

3. **复用而非重造**：`/quick` 收尾直接调 `/commit`，继承其 lint 门禁 / semantic message / Co-authored-by trailer，不重复实现——单一真源。

4. **默认当前分支直接改 + `--branch` 逃生舱**：默认不建任何分支/worktree（贴合「小函数改一下」），`--branch` 按需切轻量分支 `quick/<描述>`（仍不建 worktree）。

5. **可选 `#<issue>` 关联**：允许传 issue 号让 commit 带 `Closes #N`（只取号、不拉 issue 详情），复用已有闭环但不强制；简易流本质是「无 issue 无追踪」场景。

6. **前置心智写进 SKILL**：命中「需要计划讨论 / 需要文档追踪 / 多文件架构改 / 需追踪的 issue」信号时，SKILL 指示 AI 反问用户「是否该走正规 `/start`」，防止 quick 被滥用到本该重流程的需求上。

### 开发内容概括

- 新增 `skills/quick/SKILL.md`：参数解析（`--branch` / `#issue` / 描述三者正交）+ 前置适用性判断 + 4 步流程（可选切分支 → 直接实现 → 调 `/commit` → 轻量提示）+ 显式「明确不做」清单划清与 `/finish` 边界。
- `README.md`：skills 表引导语点明三档选择；skills 表新增 `/quick` 一行（插在 `/finish` 与 `/commit` 之间）。
- `GLOBAL_AGENTS.md`：改写「核心开发模式」段第 37 行，把三档流程做成全局规范里的唯一权威指针（worktree / `--no-worktree` / `/quick` 依次更轻）。

### 额外产物

无额外测试/脚本。本轮产物是 skill 指令文档 + 规范文本，无可单测的业务逻辑代码，验证方式为静态核对（frontmatter、表格对齐、步骤自洽）。

## 局限性

1. **`install.sh` 必须在主工作树重跑才生效**：install.sh 用 `$0` 所在目录当 `REPO_DIR`，在 worktree 内跑会把软链指向即将被删的 worktree。故本轮**未**在 worktree 内跑 install.sh，新 skill 的软链生效留到本轮合回 master 后、在主工作树 `bash install.sh`。这是所有「新增 skill」轮的共性约束，非本轮特有。
2. **`/quick` 的适用性判断依赖 AI 自觉**：SKILL 里写了「命中重信号应反问」，但没有硬性 gate 阻止误用；本质是给 AI 的校准提示，最终靠对话中人机共识。

## 后续 TODO

- 观察实际使用：`/quick` 用几轮后看「默认当前分支直接改」是否够用，还是 `--branch` 会成为高频项（若高频可考虑反转默认）。
- 观察 `[round N]` 前缀天然缺失是否带来追溯不便——目前判断简易流本就不进轮次追踪，缺前缀符合定位。

## 可沉淀项

本轮的产物**本身就是** claude-code-global 的资产（新增全局 skill），不存在「从本项目提炼、需搬到别处」的跨项目候选。开发过程中复用的经验（三源并集算轮次、worktree 内不跑 install.sh、skill 复用 `/commit`）都是本仓库既有约定的正常应用，非新增可沉淀模式。

故：暂无需向外沉淀的候选（本轮即在 claude-code-global 内开发，产物落地即沉淀）。
