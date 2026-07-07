# PLAN：/review-loop 修两处实战缺口——改用原生 codex CLI + 自动修复走 TDD 正序（round 46）

## Context

本轮修 `/review-loop` 在**真实项目首次实战**中暴露的两个缺口，均落在 `skills/review-loop/SKILL.md`、同源（skill 首次实战反馈），合并一轮：

**缺口 1（本会话主线）——调用方式被 `disable-model-invocation` 堵死**：round 45 的 Step 4 调 `/codex:adversarial-review`（及 `/codex:review`）是 codex plugin 提供的 **slash command**，frontmatter 写死 `disable-model-invocation: true`——**只能人手敲斜杠命令，Agent 无法用 Skill / SlashCommand 工具自动调起**。而 `/review-loop` 的全部价值就是「commit 前**自动**触发」，被这个约束彻底堵死。

**缺口 2（issue #51，来自 devops-bot round 5 实战反馈）——自动修复阶段没内建 TDD**：Step 6 把自动修复描述成「列问题 → **修** → 复审」，动词是「修」、无「先写红测试」步骤，诱导 Agent 直接改实现、事后补测试——正是宪法 TDD 章明令禁止的「先画靶子后射箭」。真实事故：codex 报 4 个 bug，Agent 一口气改 5 处实现才补测试，且补写的并发测试**在旧实现下根本不红**（单线程复现不了 dict-changed-size）＝**假绿**，证明不了它抓得住 bug；改成正序 TDD 后才锁死。这是通用门禁 skill 的流程缺口，非某项目特有。

**探明的事实（已实跑验证）**：

- codex CLI 有**原生子命令** `codex exec review`，非交互（实跑显示 `approval: never` + `sandbox: read-only`，与全局 `config.toml` 的 `workspace-write` 无关——review 天然只读）、输出到 stdout、**codex agent 自主翻仓库**读上下文（实跑中它自己跑了 `git status` / `cat rules/python.md` / `find` / `nl`），还自动读到双轨软链的 `~/.codex/rules/*.md` 并按项目约定 review。
- 官方那 1027 行 `codex-companion.mjs` + 15 个 lib，90% 是为「结构化 JSON 输出 + job 编排 + 状态轮询 + broker 生命周期」服务的基础设施——**对我们（CC 同步拿结果、读自然语言 review、codex 自主翻仓库）全是负担**。它还带版本号路径 `.../1.0.4/...`，随 plugin 升级漂移。**唯一值得借鉴的是** `prompts/adversarial-review.md` 里的 `<attack_surface>` 对抗清单（auth/数据损坏/回滚/竞态/空态/版本漂移/可观测性）——正是宪法念叨的「难复现盲区」的系统化 checklist，可作为 review PROMPT 注入。
- **一个硬约束**：`codex exec review --uncommitted`（flag 限定整树未提交）与自定义 `[PROMPT]`（注入 focus）**互斥**，不能同时用。

**已与用户确认的决策**：

- **摆脱官方 JS 脚本，直接调 `codex exec review`**（用户判断正确：这不是高深的事，没必要依赖版本化路径的第三方脚本）。
- **PROMPT 主导**（放弃 `--uncommitted` flag）：不用 git 输出去硬限定 review 范围，而是在 PROMPT 里让 codex agent **自己判断**「审当前工作树未提交改动」。呼应用户反复强调的「别拿 git 输出限制被 review 的范围，让 agent 区分」。这样能保住 round 45 最核心的「已定前提清单」注入机制，并顺带注入官方攻击面清单。

**要达到的结果**：`/review-loop` 的独立 review 主路径改为「CC 用 Bash 直接调 `codex exec review "<PROMPT>"`」，PROMPT 内含（范围自述 + 攻击面清单 + 已定前提清单），彻底绕开 `disable-model-invocation` 死路，且不再依赖任何 plugin 内部脚本 / 版本化路径。

## 关键设计

### 1. 调用方式：skill 内直接 Bash 调 codex（不抽包装脚本）

Step 4 主路径命令形态：

```bash
codex exec review \
  -c approval_policy=never \
  -c sandbox_mode=read-only \
  "<组装好的 PROMPT>"
```

- **`-c` 两行是显式保险**：review 子命令本就默认非交互只读，但显式钉死防未来版本默认漂移 / 用户 config 干扰，零成本高保险。
- **不抽 `scripts/codex_review.sh` 包装脚本**：命令足够简单（就一句），抽脚本反增一个要维护、要双轨软链、要 gitignore 的文件，违背「够简单就别加中间层」。CC 用 Bash 工具直接跑、拿 stdout、verbatim 呈现。
- **CC 是编排器**：不需要 job 系统 / 状态轮询——`codex exec review` 前台同步阻塞、跑完即返回 stdout，CC 拿到就分诊。

### 2. PROMPT 组装（Step 4 核心，三段式）

CC 在 Step 4 现场把 PROMPT 组装成三段（中文，因 codex 会读到中文 rules 文档、上下文一致）：

1. **范围自述**（替代 `--uncommitted` flag）：「审查当前工作树的全部未提交改动——包括 `git status` 里的 staged / unstaged / untracked。自己跑只读 git 命令确认改了什么，可自由翻阅任意未改文件看上下文（一处改动的正确性常依赖它调用 / 被调用的其它文件）。」
2. **攻击面清单**（借鉴官方 `adversarial-review.md`，中文精简版）：优先找**贵、危险、难发现**的失败——auth / 权限 / 信任边界；数据丢失 / 损坏 / 不可逆状态；回滚 / 重试 / 部分失败 / 幂等；竞态 / 排序假设 / 陈旧状态 / 重入；空态 / null / 超时 / 降级依赖；版本漂移 / schema 漂移 / 迁移 / 兼容回归；可观测性缺口。
3. **已定前提清单**（round 45 核心机制，保住）：Step 0 收集的、已由人类拍板不容再质疑的设计决策——「以下是已定前提，勿再质疑，只在此前提下找问题：<清单>」。清单为空则省略此段。

### 3. 输出噪音过滤（实跑发现，必须处理）

实跑 `codex exec review` 的 stdout 混入三类噪音，Step 4「verbatim 呈现」前 CC 要识别并滤除，只呈现真正的 review 结论：

- `git: error: couldn't create cache file '/tmp/xcrun_db-...'`（sandbox 下 `/tmp` 权限，无害）；
- `ERROR codex_models_manager: failed to refresh available models: timeout`（模型列表刷新超时，无害）；
- codex 自身的 exec trace（`OpenAI Codex v...` 头、`workdir/model/...` 元信息、`/bin/zsh -lc '...'` 命令回显）——真正的 review 结论在 `codex` 段之后。

skill 措辞点明「codex exec review 的 stdout 含环境噪音与 exec trace，呈现前剥离，只留 review 结论」。

### 4. 失败降级判据更新

Step 3 / Step 4 的「codex 可用性 + 失败降级」逻辑不变（乐观试跑 + 失败降级），但**判据换成新命令**：`codex exec review` 命令**退出码非 0 或 stdout 明显是登录 / 网络 / CLI 报错**（非 review 结论）→ 视作不可用，转 Step 5 降级本会话自审。`which codex` 可作轻量前置探测（可选，主要靠试跑失败兜底）。

## 开发内容

### A. 改 `skills/review-loop/SKILL.md`（核心，两处缺口都落这里）

**A-1（缺口 1，Step 4 换调用方式）**：

- **Step 4** 整段重写：把 `/codex:adversarial-review --wait --scope working-tree -- <前提>` 换成 `codex exec review -c ... "<三段式 PROMPT>"`；删掉关于 `--` 隔离 / companion argv / `/codex:review` vs `adversarial-review` 的整段（那是旧调用方式的约束，已不适用）；加 PROMPT 三段式说明 + 输出噪音过滤说明。
- **`## 为什么存在` / Step 3** 里凡提到「`/codex:review`」「companion」的措辞同步更新为「`codex exec review`」。
- **安全段**（Step 4 末）：`.gitignore` 保护 + codex 只读 sandbox 不碰 ignored 文件——保留，措辞微调。

**A-2（缺口 2 / issue #51，Step 6 自动修复走 TDD 正序）**：把 Step 6「有正确性问题 → 未收敛」的「2. 自动修复」子步**按问题性质分流**（已与用户确认，与宪法 TDD 章「适用范围 + 例外」一致）：

- **有清晰输入输出契约的代码类问题**（业务逻辑 / 纯函数 / 算法 / 并发）→ **TDD 正序三步**：① 先写能复现该 bug 的最小红测试，**跑它、确认在当前未修实现下失败**（写不出会红的测试＝还没真正理解 bug，先别改实现）；② 只改相关代码让红变绿；③ 跑该测试确认绿 + 回归全量。
- **硬提醒（防假绿）**：「补写的测试必须先在旧实现上验证为红——旧实现上就绿的测试是假绿，证明不了它抓得住 bug」（呼应宪法「避免先画靶子后射箭」）。
- **例外分档**：纯风格 / 机械修复，或 bug 本质无法用测试复现（纯 UI/视觉、或改的就是指令 / 文档本身）→ 按现有节奏直接改，不强求红测试。
- **修复纪律**（原有）保留：只改与本次改动相关的代码，绝不顺手动无关文件。
- line 99「修复后重跑测试」与新三步呼应，措辞微调避免重复。

其余（Step 0 已定前提清单、Step 1/2 范围与琐碎跳过、Step 5 降级、Step 6 每 3 轮人工闸口 + 留痕）**逻辑不变**，仅个别命令引用同步。

### B. 改 `GLOBAL_AGENTS.md`（宪法「独立模型 review」小节，line 86）

把 `（走 /codex:review / /codex:adversarial-review）` 换成 `（走 codex exec review 原生子命令，见 /review-loop skill）`。其余措辞不动。

### C. 改 `README.md`（line 96 Skills 表 `/review-loop` 行）

把 `由 codex（/codex:review）独立 review` 换成 `由 codex（codex exec review）独立 review`。line 87 / 198 无具体废弃命令引用，不动。

### D. `skills/commit/SKILL.md`（line 12）

只引用了「调 `/review-loop`」，未硬编码 `/codex:*` 命令——**不需改**（细节以 /review-loop 为单一真源，正确解耦）。核对确认即可。

## 不做

- **不抽包装脚本**（`scripts/codex_review.sh`）：命令够简单，抽脚本反增维护面。
- **不碰官方 companion 脚本 / plugin**：完全绕开，不 patch、不封装它。
- **不改 round 45 的核心机制**：自动收口环、每 3 轮人工闸口、已定前提清单、审≠写独立性判定、整树 review + gitignore 保护——全部保留，本轮只换「怎么调 codex」这一层实现。
- **不引入结构化 JSON 输出**：CC 读 codex 的自然语言 review 分诊足矣，不需要 schema。

## 涉及文件

- 改：`skills/review-loop/SKILL.md`（A-1 Step 4 换调用方式 + A-2 Step 6 自动修复走 TDD 正序）——**核心，两处缺口都在这**
- 改：`GLOBAL_AGENTS.md`（line 86 命令引用）
- 改：`README.md`（line 96 命令引用）
- 核对不改：`skills/commit/SKILL.md`（解耦正确，无废弃命令硬引用）
- 本轮产物：`docs/46-review-loop两处实战缺口/`（PROMPT.md / PLAN.md / REVIEW.md / SUMMARY.md）
- **无需 `install.sh`**：review-loop 目录已存在且已双轨软链，仅改内容（软链自动生效）。

## 测试 / 验证

改的是指令文档（skill / 宪法 / README），非可单测的业务逻辑，故本轮改动本身无单测可写；但**必须端到端实跑验证**——缺口 1 恰恰是「没实跑就上线」暴露的：

1. **造真实代码 diff 实跑新命令**：在本仓造一个含真实缺陷的临时改动，跑 Step 4 的 `codex exec review -c ... "<三段式 PROMPT>"`，确认：① 非交互跑通、② codex 读到改动、③ 攻击面清单生效（能指出注入类问题）、④ 已定前提段生效（对清单内决策不质疑）、⑤ CC 能从 stdout 滤除噪音留下 review 结论。跑完清理临时改动。
2. **本 skill 自举**：本轮 diff（改的是 skill / 宪法 / README 指令文件——**绝不跳过 review**）用**新的** `codex exec review` 跑一遍独立 review（走 `/review-loop` 自身），迭代至 clean——既验证新命令、又符合「指令文件必须过 review」。
3. **降级路径走查**：`codex` 命令临时不可用时（或读逻辑走查）确认 Step 5 停下告知用户 + 本会话自审标注生效。
4. **一致性**：`grep -rn 'codex:review\|codex:adversarial-review\|codex-companion' skills/ GLOBAL_AGENTS.md README.md` 确认再无对废弃 slash command / companion 脚本的硬引用。
5. **缺口 2（TDD 段）走查**：Step 6 新的分流三步在「代码类 bug」与「文档/机械修复」两条路径下措辞自洽，与宪法 TDD 章无冲突、无重复。

## round 46 收尾

`/finish` 默认流程（SUMMARY → devtree → commit → worktree rebase+FF+清理）。本轮 diff 全由 CC 编写 → commit 前的 `/review-loop` 走**新的** codex 独立 review（自举，见验证 2）。commit / PR 写 **`Closes #51`** 自动关 issue（缺口 2 来源）；缺口 1 是实战发现、无关联 issue，记 SUMMARY 即可。
