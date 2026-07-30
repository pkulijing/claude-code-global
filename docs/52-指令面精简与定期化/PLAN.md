# Round 52：指令面按 Claude 5 精神精简，并把「精简」定期化

## Context

**为什么做这件事。** Anthropic 发布 [The new rules of context engineering for Claude 5](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)，公布对 Opus 5 / Fable 5 移除了 Claude Code 系统提示的 **80% 以上，编码 eval 无可测量的性能损失**。核心判断是旧约束过度限制、且系统内部存在互相冲突的指引。

本仓的指令面正是那个形态，且**四个月 4.8 倍、从未净减**（32,495 → 156,689 字符）。人类的原话是「你总在某次犯过错误之后加一些关于当时怎么犯的错的冗长的描述」——这个观察准确，但根因不是「记了 WHY」，而是**形态**：写成了叙事而非判据，且同一条规则在多处各写一遍。

**预期结果**：① 一次性把重复与叙事压下去（本轮，人 review）；② 留下一条能逐周把指令面拉回平衡的定期任务（本轮产出，routine 上线后自动跑）。

**已决**（人类开轮时拍板，见 `docs/52-指令面精简与定期化/PROMPT.md`）：

1. 顺序 = **先精简，再把判据固化成 routine**（判据从实操中提炼，不先验编造）
2. 力度 = **三板斧**（去重 + 细则上提为判断原则 + WHY 从叙事压成一句）；**不做**逐条 ablation 删除
3. **`playbooks/*.md` 本轮不碰**——交给 routine 上线后逐周做，同时作为 routine 的首批真实试验场
4. **不新增机械断言清单**——防蒸发靠 PR/账本三列表格 + `/finish` 人工 review
5. 分支基点 master `38d3441`（round51 已先行合入并实测确认生效）

**本轮精简对象**：`GLOBAL_AGENTS.md`（9,922）+ `skills/*/SKILL.md`（94,086）+ 本仓 `CLAUDE.md`（5,042）= 109,050 字符。

---

## 关键发现：重复是最大头，且文档自己承认了双写

`sync-project-config` 写着「与 bootstrap Step 3.3.7 **同一份，改动时两处同步**」「逻辑**等同** bootstrap 的 Step 3.5」；`commit` 第 4 步写着「细节以 `/review-loop` 为**单一真源**」，紧接着复述了 ~700 字符。

| 重复内容 | 出现处 | 处置 |
| --- | --- | --- |
| review-loop 机制（三要素并闸 / 置信过滤 / 2 轮留痕） | 宪法「核心开发模式」+ 宪法「提交前 review」+ `review-loop` frontmatter + 正文「loop 是什么」+ Step 6 + `commit` 第 4 步 = **6 处** | 真源留 `review-loop`；宪法两段并一段只留判据与指针；`commit` 第 4 步收成两三句 |
| 模板机制（fragment TOML/JSON 合并、变体组落地、python-uv 可跑化、react-vite 装依赖） | `bootstrap` 3.3.6/3.3.7/3.5/3.5b + `sync-project-config` 2.4/4.3/4.4/4.5 + 项目 `CLAUDE.md` = **3 处近乎逐字** | 抽 `templates/MECHANICS.md`，三处改指针 |
| `Closes #N` 多 issue 各占一行 | `finish` Step 4 + `routine-docs` Step 4 | 真源留 `commit`，两处指针 |
| wontfix 归档手法 | `finish` Step 2 + `sync-project-config` BACKLOG 迁移 | 真源留 `finish` Step 2 |
| round 编号一致性检查 | `finish` Step 4.5 + `rebase` | 真源留 `rebase` |
| platform_issue helper 契约（三轴 label、exit code 降级） | `finish` / `bootstrap` / `sync-project-config` / `backlog` 各复述 | **真源 `scripts/platform_issue.md` 本来就在**，四处改纯指针 |

## 三板斧判据（本轮的操作定义，也是 routine 的判据来源）

**允许删除（封闭清单，超出即不删）**

1. 已在别处有单一真源的**重复表述**——必须同时留下指针（「细节见 X」），否则算蒸发
2. 成组的同向细则 → 上提为一句判断原则（blog shift 1）
3. 事故 WHY 的**过程叙事**（谁在哪轮怎么错的、返工了几处）→ 压成结论一句
4. 指向已删机制 / 文件 / 命令的**失效引用**
5. Agent 已在系统提示 / 工具描述里被告知的重复（如「Agent 工具 `description` 是必填字段」）

**禁止删除**

- 事故 WHY 的**结论**（可以压缩，不可消失）
- 安全禁令与硬边界（`ff-merge` 相关、`--force` 禁令、`Codex 绝不写 Claude 身份`、fork PR 防线、prompt-injection 链条）
- 非标约定（本仓特有、模型推不出来的：三轴 label 强制、`__root__`/`__subpath__` 语义、marker schema）
- **拿不准就保留**（继承 `/doctor` check 3 的 "When unsure, keep it"）

**只允许搬走不允许蒸发**：每条删减在账本里记三列 —— **删了什么 / 依据上面哪条判据 / 这条信息现在从哪读得到**。

---

## 实施计划

### 阶段 0 · 量化基线（先有数）

**新增 `scripts/context-budget.py`**（零第三方依赖，裸 `python3` 可跑；`scripts/` 是逐文件软链，新增后需重跑 `bash install.sh`）：

- `measure` — 扫指令面各文件，输出字符数 + token 估算 + 分类（常驻 / 懒加载），支持 `--json`。
  **token 估算必须标定，不能按英文 4 字符/token 估**：本轮由 `/context` 实测标定 `GLOBAL_AGENTS.md` 9,922 字符 = 8k token（中文 ≈1.24 字符/token，英文经验值会低估 3 倍）。模型取 `cjk/1.24 + 非cjk/4`，脚本内注明标定来源。
- `delta --since <git-ref>` — 用 `git show <ref>:<path>` 取旧版本对比，算增长率。**无状态文件**：默认 ref 由 `git rev-list -1 --before=<4周前> HEAD` 算出，不打 tag、不落基线文件（回应 issue 里「基线存哪」的待决问题）。
- `check-refs` — 扫指令文件里的跨文件引用（`playbooks/*.md`、`references/*.md`、`~/.claude/scripts/*.md`、`skills/*/SKILL.md` 等），断言目标存在。**这是「搬走而非蒸发」的机械兑现**：指针指不到东西 = 信息实际丢失。零维护文件，不同于已被否掉的断言清单。

**测试（TDD 正序）**：`docs/52-指令面精简与定期化/test_context_budget.py`，标准库 `unittest`、零依赖（跟随 round51 `docs/51-*/test-unlink-legacy.sh` 的轮次内测试脚本先例）。先写红测试再实现：token 估算对纯中文 / 纯英文 / 混排的边界、`delta` 对「文件新增 / 删除 / 改名」的处理、`check-refs` 对失效引用的检出。

跑一遍 `measure` 存进 `docs/52-*/BASELINE.md`，作为后续每步的对照。

### 阶段 1 · 抽共享 reference，消灭已承认的双写

**新增 `templates/MECHANICS.md`**（`templates/` 是目录级软链 → 两端 `~/.claude/templates/MECHANICS.md` 均可达；顶层 `.md` 文件不是子目录，不会被 `bootstrap` Step 3.1 的「非下划线开头子目录 = stack」逻辑误当成 stack）。承载：

- `__root__` / `__subpath__` 落点语义
- fragment 合并（`pyproject.toml.<section>.fragment` TOML 段合并 + `.vscode/*.json.fragment` JSON 合并）
- 变体组 `<target>.variant.<key>` 的落地与 marker `variants` 记录
- python-uv / python-uv-workspace 可跑化四步、react-vite `npm install`
- 迁移去重（普通文件 → fragment / → 变体组）

`bootstrap` 与 `sync-project-config` 只留「何时去读 MECHANICS.md」的指针 + 各自流程特有的部分（bootstrap 的冷启动交互、sync 的四象限 diff 与 skipped 语义）。项目 `CLAUDE.md` 里 `templates/` 那条长条目同样收成一句 + 指针。

### 阶段 2 · review 链路单一真源

- 宪法「核心开发模式」与「提交前 review」两段**并成一段**，只留：什么时候跑、收敛判据一句、2 轮留痕放行一句、指针到 `/review-loop`。删掉档位规格、成本三规则、盲区实证的复述。
- `commit` 第 4 步：删掉整段复述，留「调 `/review-loop`，迭代到 clean 才继续；放在 lint 之前因为它会自动改代码」。
- `review-loop` 自身：frontmatter description 收成一句（它是 skill listing 的常驻成本）；正文「loop 是什么」与 Step 6 的三要素并闸只写一遍；事故叙事（round 47/48/50、grpc.aio、32 万 token 实测）压成结论句。

### 阶段 3 · 宪法三板斧

`GLOBAL_AGENTS.md` 9,922 字符，「核心开发模式」章独占 71.6%（6,797）——主战场。

- 需求管理 / 需求生命周期 / TDD / 提交前 review 四小节：细则上提为判断原则，事故叙事压句
- 「文档记录规范」与各 skill 的复述去重
- blog 对 CLAUDE.md 的直接指引（"lightweight … spend most of the tokens on gotchas"）同样适用于宪法：保留判断原则与非标约定，删掉可由模型推导的部分

### 阶段 4 · 逐 skill 三板斧 + progressive disclosure

对 `finish` / `routine-docs` / `bootstrap` / `sync-project-config` / `devtree` / `rebase` / `start` / `quick` / `backlog` / `pybump` / `paper-read`：三板斧 + 超阈值者拆 `skills/<name>/references/*.md`（先例 `skills/finish/references/readme-review.md`，`skills/<name>/` 是目录级软链，子目录直接可达）。

拆分候选：`finish` Step 8 worktree 收尾细节、`routine-docs` 的 prompt-injection 链条论证与注册说明、`sync-project-config` 的四象限与 skipped 语义细则。**每处拆分必须在 `SKILL.md` 留「何时去读哪个 reference」的指针**。

**参考目标**（不是配额，绝不为达标而删；实际以账本判据为准）：

| 文件 | 现状 | 参考目标 |
| --- | ---: | ---: |
| `GLOBAL_AGENTS.md` | 9,922 | ~5,500 |
| `skills/sync-project-config` | 16,501 | ~10,000 |
| `skills/routine-docs` | 14,311 | ~9,000 |
| `skills/bootstrap` | 11,521 | ~7,000 |
| `skills/review-loop` | 10,731 | ~7,000 |
| `skills/finish` | 10,476 | ~7,000 |
| `CLAUDE.md` | 5,042 | ~3,000 |
| `templates/MECHANICS.md` | — | +~4,000 |
| **合计** | **109,050** | **~76,000（-30%）** |

### 阶段 5 · 把判据固化成 `/routine-slim`

**新增 `skills/routine-slim/SKILL.md`**，结构对标已上线的 `/routine-docs`（同一条云端 routine 形态，PR 即审批闸）：

- **Step 0 环境判定 + 前置闸**：云端无 `gh`（`scripts/platform_issue.py` 整个不可用）→ 走内置 GitHub MCP；工作树干净、在默认分支且与远端同步
- **Step 1 阈值触发**：`context-budget.py delta --since <4周前>`，增长 ≤15% → **空转退出**并打印数字，不提噪音 PR
- **Step 2 选目标**：白名单内按 token 排序 + 跨文件重复检测，挑本次要动的
- **Step 3 三板斧**：本文档「三板斧判据」原样落进剧本（允许删除封闭清单 + 禁止删除清单 + When unsure, keep it）
- **Step 4 出 PR**：描述**强制三列表格**（删了什么 / 依据哪条判据 / 现在从哪读得到）+ `check-refs` 结果 + 前后 token 对比
- **无人值守分岔契约表**：每个「停下问人」的分岔 → 映射为「不改、记入 PR 描述」
- **`--dry-run` 一等公民**，上线前必跑并人过目

**白名单 / 黑名单（安全边界，硬钉）**

| | 内容 |
| --- | --- |
| **可自动改** | `skills/*/SKILL.md`、`skills/*/references/*.md`、`playbooks/*.md` |
| **只报告不动手** | `GLOBAL_AGENTS.md`、本仓 `CLAUDE.md` —— 删减候选单列一节写进 PR 描述，人来定 |
| **永不碰** | `skills/routine-slim/**`（自身）、`skills/routine-docs/**`（另一条自动写 master 的路）、`.github/**`、`install.sh`、`scripts/**`、`hooks/**`、`templates/**`、`docs/**` |

理由：一条能自动改 `skills/` 的 routine 就是能改门禁自身规则的 routine；宪法与两条 routine 的剧本必须留在人手里。

**cron**：周日 01:00 UTC（= 北京时间周日 09:00；cron 走 UTC、最小间隔 1 小时，见 `playbooks/cloud-routine.md`）。注册是**人的动作**（在 claude.ai 建 routine，`sources` 挂本仓，prompt 只留指针）——SKILL 末节给出 prompt 模板，同 `/routine-docs`。

**项目 `CLAUDE.md`**：把现有「本仓有一条云端定时 routine」扩为两条，并注明 `/routine-slim` 的白名单是安全边界。

### 阶段 6 · 账本与收尾

`docs/52-指令面精简与定期化/SLIM-LEDGER.md` —— 本轮**全部删减的三列账本**，按文件分组。这是 `/finish` 时人工 review 的主要对象（删除型 diff「少了什么是看不见的」，账本是唯一护栏），同时也是 `/routine-slim` PR 描述格式的样板。

---

## 验证

精简的正确性无法用单测断言，故分四层，逐层可执行：

1. **`context-budget.py` 自身**：`python3 -m unittest` 跑 `docs/52-*/test_context_budget.py`，全绿。
2. **引用可达性**：`python3 scripts/context-budget.py check-refs` 零失效引用——机械兑现「搬走而非蒸发」。
3. **本轮自带的端到端 dogfood**（最强的一层）：本轮每个 commit 都会真实调用被精简的 skill 自身——`/commit` → `/review-loop` → 最后 `/finish` → `/devtree`。**如果精简把它们改坏了，本轮自己就跑不完。**额外单独验：`bash install.sh` 幂等跑通（`templates/MECHANICS.md` 与新 `scripts/context-budget.py` 正确落链，`~/.claude/templates/MECHANICS.md` 可读）。
4. **`/routine-slim --dry-run` 人过目**（上线前硬要求，`playbooks/cloud-routine.md` §5 已立此规）：本机跑一次，检查阈值判定、选目标、三板斧提议是否合理。`/routine-docs` 上线前那次 dry-run 当场改掉两条规则——同样的收益预期。

**量化对照**：收尾再跑一次 `measure`，与 `BASELINE.md` 对比，降幅写进 `SUMMARY.md`。

## 风险

- **最大风险：LLM 精简器删掉「为什么」。** 缓解 = 封闭的允许删除清单 + 禁止删除清单 + When unsure keep it + 三列账本 + `/finish` 人工 review。人类已明确否掉机械断言清单，故**人工 review 是最后一道闸**，账本必须写全。
- **本轮改的是指令规则文件本身**——按宪法属「绝不自动跳过 review」类别，每个 commit 都走 `/review-loop`。
- **精简 `/commit` 与 `/review-loop` 时有自举风险**：改坏了当轮就提交不了。这两个文件的改动单独成 commit、改完立刻用它们自己提交一次验证。
- **`templates/MECHANICS.md` 落点假设**已核实：`templates/` 目录级软链（`install.sh:374`）、`bootstrap` Step 3.1 只把**子目录**当 stack，顶层 `.md` 不受影响。
