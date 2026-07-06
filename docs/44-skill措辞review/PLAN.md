# PLAN：skill 措辞集中 review（round 44）

## Context

经约 40 轮迭代，`skills/` 下多个 `SKILL.md`、`rules/` 领域规则、`GLOBAL_AGENTS.md` 宪法都越写越长。这些都是**进 context 的指令性文档**（skill body 触发时整段加载、rules 命中触发条件时被 Read、GLOBAL_AGENTS 每 session 常驻），冗长直接吃 token 预算、稀释关键指令。本轮借 `skill-creator` 的「什么是好 skill」判据作精简 rubric，同一套 rubric 同时用于 skill / rules / 宪法，产出「清单先行、用户拍板、再统一落地」的精简。

**硬底线（贯穿全程）**：只动措辞与结构，**不改行为语义**。这些是被真跑/真遵循的指令——所有实质规则、分支逻辑、踩坑防御、`why` 核心必须保留。省行不是 KPI，零行为回归才是。

**范围（行数为 review 前）**——超过 100 行的都纳入：

- **skills**：`sync-project-config` 374 / `finish` 283 / `bootstrap` 249 / `devtree` ~230（含 round42 新增的表格规则）/ `rebase` 141。
- **rules**：`python.md` 295 / `ros2.md` 172。（frontend 69 / lark 33 / shell 33 本轮不动）
- **宪法**：`GLOBAL_AGENTS.md` 161。
- 合计 ~2235 行。

已确认决策：① 清单先行、拍板后逐个落地；② 力度中等（允许下沉 + 重组）；③ 本轮不沉淀 skill（后续 TODO）；④ labels 契约下沉 `scripts/platform_issue.md`；⑤ finish Step 6 下沉 `finish/references/readme-review.md`；⑥ 范围扩到 rules + GLOBAL_AGENTS；⑦ GLOBAL_AGENTS 的孪生化「rules 指针」提取到一处、各领域章节只留触发句。

**目标量级**：~2235 → ~1740（省约 22%），**且零行为回归**。

## master 已前进（本 worktree 基于旧 master，finish 阶段 rebase 吸收）

`a757318` 起 master 新增 round42（碰 devtree：+10 行「表格紧凑单空格」规则，配合 `.prettierignore`，**是真实约束、保留但精简措辞**）、round43（碰 template，不碰本轮目标）。落地后 finish 阶段 rebase 到最新 master，冲突面仅 devtree 那 10 行。

## 精简 rubric（源自 skill-creator，6 条可操作检查项）

1. **重复叮嘱（DRY）** → 收敛一处，其余引用。
2. **过度展开的历史注释**（`round-XX`、旧版对比、踩坑来龙去脉）→ 留 why 的**结论**、删演化史。呼应 `rules/python.md §3.4`。
3. **why 过度铺陈** → 压到 1 句、保因果核心。
4. **僵硬 MUST/ALWAYS/NEVER 堆砌** → 软化为解释性。**判据**：违反是否造成真实事故？是→保留强调；否→软化。
5. **可下沉细节（progressive disclosure）** → 下沉 `references/` 或脚本同目录文档。
6. **表格/散文冗余** → 二选一留信息密度高的（通常**留表删散文**）。

## 机制约束（已核实）

- `~/.claude/skills/<name>` 是**逐 skill 目录级软链** → skill 内新建 `references/` 随软链生效，同目录相对引用 OK。
- **跨 skill 共享 references 不干净**（穿两条软链的脆弱相对路径）→ 跨 skill 重复走「就近各留最简」，不硬合并。
- `~/.claude/scripts/` 是**逐文件软链**（非目录级）→ 新增 `scripts/platform_issue.md` **必须重跑 `install.sh`** 才软链过去。skill body 引用 `$HOME/.claude/scripts/platform_issue.md`，重装后即在。

## 落地方案（拍板后逐个 skill 执行，逐个给 diff）

### 0. 先建两个下沉文件（跨 skill 共享片段的新真源）

- **`scripts/platform_issue.md`**（新建）：承接 labels helper 完整契约——`label-sync-from-file` 语义、gh/glab dispatch、color 格式转换、exit 2/3/4 降级提示、三轴 label + 零-label 拦截。bootstrap §3.3.5 / sync §6 / finish §3.5 三处各留一句「helper 按平台自动 dispatch；exit 2/3/4 = 平台未知/auth失败/CLI缺失，降级详见 `scripts/platform_issue.md`」。**落地后需 `bash install.sh` 软链。**
- **`skills/finish/references/readme-review.md`**（新建）：承接 finish Step 6 README-review 整块（触发清单/不触发/数据源/子步）。finish body Step 6 收缩为一句「命中触发则按 `references/readme-review.md` 执行」。

### 1. sync-project-config（374 → ~285，-90）

- fragment 迁移去重（§2.4 line 170-173）**红线整块保留**（防「机制迁移误判为真删除」删用户配置）。
- `len==0/1/>=1` 三态注解 → §2.1 尾集中声明一次，后续各节引用；**保留 line 180 防御性 why**（防 AI 给 `_common` 造假 stack 条目）。
- §2.6 样例 TODO 大块（line 194-209）→ 压到 3-4 行示意（是「长啥样」示例、非逐字契约）。
- skipped 语义（§2.5）与 §6 更新策略重叠 → 合并到一处。
- labels 契约 → 引用 `scripts/platform_issue.md`。
- fragment 合并规则**不跨 skill 下沉**（与 bootstrap 语境不同：diff-merge vs 复制），仅本 skill 内 §2.4 一处权威、其余引用。

### 2. finish（283 → ~213，-70）

- **预算主战场在 Step 6 下沉**（-25），不在 `Closes #N`。
- Step 4 `Closes #N` 规则块 + 正例（`Closes #13/#20/#23`）+ 反例（「含逗号也不行」）**整块保留**（坑的杀伤力在于不看反例就犯）；Step 7 收缩为「按 Step 4 硬规则，多 issue 各占一行」的引用。
- Step 2「刻意不做归 wontfix」手法与 Step 3.x issue-create/label 校验/失败兜底重复 → 手法定义一次、其余引用；**零-label 拦截 + 「绝不去 --label 重试」保留强调**（#12 事故）。
- Step 8 收尾开关：**留对照表、删各节顶部散文注解**（收敛为「见对照表」）。
- labels 契约 → 引用 `scripts/platform_issue.md`。
- round 编号一致性（Step 4.5）与 rebase 就近各留最简（见下）。

### 3. bootstrap（249 → ~194，-55）

- **不与 sync 硬合并 fragment 逻辑**（语境不同）；本 skill 内 §3.3.6 一处权威。
- §3 超长导言（line 67，近 200 字）→ 压一半，与 §3.3 去重。
- `--bare` vs `--package` 历史对比（line 164）→ **只删历史半句**（「旧版用 --bare…」），**留结论半句**（「--package 产物已是空 **init**.py」，防 AI 疑惑会否生成 hello world）。
- labels 契约（§3.3.5）→ 引用 `scripts/platform_issue.md`。
- uv 可跑化 §3.5.x 与 sync §4.4.x 重复 → 就近各留最简（不跨 skill 下沉）。

### 4. devtree（~230 → ~190，-40）

- 「从 Epic 结构完全重建」原则 → 开头强调一次，执行流程各步的复读收敛为引用。
- **Mermaid 防御规则四条一字不动、不下沉**（违反则图渲染失败/节点消失，是核心产出质量门）。
- **输出格式模板保留**（AI 逐字对照生成的产出契约）。
- 「旧顺序颠倒」一次性迁移段保留（幂等迁移）。
- **round42 新增的「表格紧凑单空格」规则**：约束保留（配合 `.prettierignore` 消 diff 噪音），但现在散文段 + `> 注意` blockquote 把「紧凑 vs 对齐」讲了两遍 → 压成一段（rubric #6）。

### 5. rebase（141 → ~113，-28）

- **必停清单（原则 #6 的 8 项）完整保留、一字不动**（安全内核、集中真源）；各阶段「XX 属必停项」的就地提醒收敛为「命中必停清单（原则 #6）」引用。
- 备份 tag / FF-only / 禁 fallback merge 的多处强调 → 合并重复句，**保留强调**（真实安全约束）。
- round 编号一致性检查与 finish Step 4.5 几乎逐字重复 → **就近各留最简**（不跨 skill 下沉：二者语境略异，且都只 5-8 行，重复成本低于跨软链耦合）。

### 6. rules/python.md（295 → ~245，-50）

**这是 rules 里最长、精简空间最大的**。用它自己的 §3.4「注释写当前真相不写演化史」精简它自己。

- **§5 打包发布（5.1~5.4，约 78 行）是重点**：细节极多、每节都有长 why + 代码块。5.4 的「应用内更新自检骨架」两个函数代码块 + 5 步散文有重叠（散文讲一遍、代码再演示一遍）→ 留代码块、散文压成引导句。5.2 GitLab registry 两个坑的 why 铺得很开 → 压。
- **§2.3 src 布局命名撞车（排障）**：现象 + 误导点 + 两场景 + 判据 + 解法，展开充分但**是真踩坑排障**（呼应它自己在 CLAUDE.md 里被引用）→ 保留结论、压措辞。
- **§3 的 7 条开发风格**：每条都有 rule / 为什么 / 适用边界三段式，部分「为什么」铺陈过长（如 3.2 包内绝对 import 列了 5 条理由）→ 压理由列表，保留 rule 与边界。
- **红线保留**：所有 rule 本身、escape hatch 触发条件、踩坑判据一字不动。

### 7. rules/ros2.md（172 → ~150，-22）

- **§4.6 source-time hook**：「为什么纯 ament_python 不触发」那段 colcon-ros 内部机理铺得很细（一整段讲 package.dsv 写死逻辑）→ 保留结论（纯 ament_python 做不到、要切 ament_cmake_python）、压机理细节。
- **§5 双链路**：与 §5 pip 依赖有概念重叠的导言 → 压。CMake 代码块保留（是照抄契约）。
- **§8 新增包检查清单**（14 项 checklist）保留（是执行契约、逐条核对用）。
- 红线保留：build 顺序、依赖三步、导出规则、CMake 代码块。

### 8. GLOBAL_AGENTS.md（161 → ~135，-26）

- **孪生化 rules 指针提取（已确认）**：开头「领域规则文档（rules/）」节已讲通用规则，但后面 Python/前端/ROS2/lark/shell **5 个章节各重复**「CC 端路径 `~/.claude/rules/X.md` / Codex 端路径 `~/.codex/rules/X.md` / 触发条件」三行 → 通用「双端路径 + 必须主动 Read」规则在开头节讲**一次**，5 个领域章节各压成一句「触发条件：涉及 X → 读 `rules/X.md`」。**机制安全**（已核实：GLOBAL_AGENTS 单文件软链到两端主文档，同一文本被两端读，故开头一次讲「你在哪端读哪个路径」零信息损失）。
- **红线保留**：称呼/语言约定、核心开发模式、需求生命周期、TDD、文档规范、git 规则（Co-authored-by 表 + 判据）、环境变量——这些是宪法实质，只压措辞不删条款。

## 落地顺序与产出形态

按用户已选「清单先行再逐个落地」：

1. 先建 §0 两个下沉文件（`scripts/platform_issue.md` + `finish/references/readme-review.md`）；
2. 逐个精简、**每个落地后单独给一段 diff 摘要**（改了哪些段、省了多少行、确认哪些红线原样保留）。顺序：先 skill（sync → finish → bootstrap → devtree → rebase），再 rules（python → ros2），最后 GLOBAL_AGENTS（最敏感、放最后单独确认）；
3. 全部落地后跑 `bash install.sh`（新增 `scripts/platform_issue.md` 逐文件软链需重装）。

## 验证

1. **零行为回归自查**：每个文件改后 Read 全文，对照原文逐条核对——所有实质规则、分支逻辑、踩坑防御都在。重点红线清单：`Closes #N` 反例 / FF-only / 必停清单 / 零-label 拦截 / fragment 迁移判定 / Mermaid 四防御 / devtree 表格紧凑规则 / python escape hatch 触发条件 / ros2 build 顺序 / 宪法 git 署名表。
2. **下沉指针可达**：从各 body 能定位到 `scripts/platform_issue.md` / `finish/references/readme-review.md`；重装后 `~/.claude/scripts/platform_issue.md` 存在。GLOBAL_AGENTS 孪生化提取后，5 个领域触发句仍能各自指向正确 rules 文件。
3. **量级核对**：`git diff --stat` 净减 ~495 行（2235→1740），与预估同量级。
4. **install.sh 幂等**：重装无报错，5 skill + rules + 主文档软链仍生效。
5. **rebase 吸收 master**：finish 阶段 rebase 到含 round42/43 的最新 master，devtree 那 10 行冲突逐个解。

## 后续 TODO（记入 SUMMARY，本轮不做）

- 若 rubric 验证有效，下一 round 把这套 6 条 rubric + 「按片段性质二分去重」+「progressive disclosure 下沉」固化成 `/skill-review`（或 doc-ameliorator，因范围已含 rules/宪法）可复用 skill。避免先造工具后发现 rubric 不对。
