# REVIEW · round 57

## 开发单元 1 —— helper 吐出 issue 状态（`scripts/platform_issue.py`）

### 元信息

- **档位**：默认档，3 个并行 `code-reviewer`（角度 ①契约与装配 ②缺陷定向扫描 ③项目规范合规）
- **是否降级**：**否** —— `review-orchestrator` 委派实际发起并成功，编队档位由 `agents/*.md` frontmatter 钉死
- **闸 A（运行验证）**：`python3 scripts/platform_issue.py --self-test` + 真机冒烟（`issue-view 91` / `114` / `--with-comments` / `issue-list`）
- **迭代轮数**：2 轮（第 1 轮 1 条 finding → 修 → 第 2 轮 clean），**收敛**

### 第 1 轮：1 条 finding（置信 98，已修）

**`scripts/platform_issue.py` 内置的 `cmd_self_test()` 硬编码着旧 schema 的期望值，改了 schema 没同步 → `--self-test` exit 1、7 条 FAIL。**

实测证据（reviewer 跑出来的，非推断）：

```
$ python3 scripts/platform_issue.py --self-test; echo "EXIT=$?"
FAIL: normalize_issue gitlab: {..., 'state': 'open', 'stateReason': ''}
FAIL: normalize_issue github: ...
FAIL: build_issue_list_cmd(github, limit=100, repo=None): ...
FAIL: build_issue_list_cmd(github, limit=30, repo='o/x'): ...
FAIL: issue-list gitlab normalize: ...
FAIL: build_issue_view_cmd(github, 7, with_comments=False): ...
FAIL: build_issue_view_cmd(github, 7, with_comments=True): ...
EXIT=1
```

**为什么自己没发现**：新写的 19 个 unittest 用例全绿，而这个脚本**自带另一套 self-test**，两者互不知情。这正是「独立 context」的价值 —— 写 diff 的人只会跑自己刚写的那套。

**修复分两部分**：

1. 同步全部 7 处过期期望值。
2. **结构决定**：把 19 个 unittest 用例并进 `cmd_self_test()`（新增 `state_cases` / `reason_cases` 两组），删掉独立文件 `docs/57-*/test_platform_issue.py`。

第 2 部分不是 finding 要求的，是顺着它暴露的问题往下推一步：`skills/routine-dev/SKILL.md:186` 明写该脚本的门禁是 `--self-test`，**留两套测试等于新增的 state 逻辑不在被文档承认的门禁覆盖内** —— 将来 routine 改这个脚本，门禁绿着而 state 归一已经坏了。这是本仓最忌的「静默失效的门禁」形态。配套依据是宪法「写代码要像周围的代码」：这个文件的既有惯例就是内联 self-test（round 52 建立独立测试文件的先例成立，是因为 `context_budget.py` 根本没有内联 self-test）。

### 第 2 轮：CLEAN

三方独立核验，**均未发现置信 ≥80 的 finding**：

- **原 finding 已消除** —— 三个 reviewer 各自实跑 `--self-test`，`OK` / exit 0。
- **新增用例逐条手算复核** —— 8 条 `state_cases` + 4 条 `reason_cases` 代入归一逻辑重算，期望值全部正确，无「复述实现」型断言。
- **合并后无覆盖损失** —— 被删的 19 个用例语义上在 `cmd_self_test()` 全部找到等价物，含 `--with-comments` 路径与「默认不带 comments 字段」。
- **无悬空引用** —— 那个文件从未被 git 追踪；全仓 grep 只命中 `PLAN.md` 里刻意保留的历史说明。
- **无遗漏的旧 schema 硬编码**（第 1 轮正是栽在这里，故正面再扫一次）—— 全仓 grep `number,title,body,url,labels` 只命中脚本自身（已同步）与 `docs/54-*/PLAN.md`（历史文档，非可执行依赖）；`hooks/` / `install.sh` / `templates/` 均无。

### 低于阈值、未上报的观察（<80）

| 项 | 说明 |
| --- | --- |
| `"CLOSED "`（尾随空格）未 `.strip()` 会被判成 `open` | 判错方向落在既定的「判不出算 open」安全侧，且 `gh` / `glab` 实际输出不会产出带空白的字段值。不改。 |
| `state=0/False/list/dict` 等非字符串 | 已复核全部归一为 `open`，不抛异常。符合设计。 |
| `/triage`、`/start` 的内联 schema 尚未提及新字段 | 命中已定前提 5（后续 commit 的范围），不计本轮。**已记入待办，别在 commit 2 漏掉这块接线。** |

## 开发单元 2 —— `/start` 的远端对齐（`skills/start/SKILL.md`）

### 元信息

- **档位**：默认档，角度 ①②③
- **是否降级**：**否**。第 1 轮由 `review-orchestrator` 正常跑完（那条 85 分 finding 就是它给的）。**第 2 轮它返回「还在等角度 ②」**，催一次仍是「还在等」；第二次明确要求「别等了、自己按 `angles.md` 补审那个角度」后，**它完整跑完并给出了 78 分那条 finding**。
  **事后修正（重要）**：我当时把这归因为「orchestrator 收不回结果 / 不可用」，并在开发单元 3 直接绕过它。**这个判断下重了** —— 本轮共调它 5 次、**4 次正常**，事后用同一份 diff 做的对照实验也跑通了。真正缺的是**任务书里没写「拿不到子 agent 结果时怎么收尾」**，补上一句即恢复正常。详见 `SUMMARY.md` §3.6。
  **额外观察**：角度 ② 的 reviewer 反馈它 `SendMessage` 给 `review-orchestrator` 时报 `No agent named 'review-orchestrator' is reachable`。但结果本来就经 Agent 工具返回值回传、不靠 `SendMessage`，故这条**不是** orchestrator 空等的原因。
- **闸 A（运行验证）**：指令文件无可运行单元，判 N/A；以**逐字抠出文档里的命令实跑**代偿（见下）
- **迭代轮数**：2 轮，收敛

### 第 1 轮：1 条 finding（置信 85，已修）

**`skills/start/SKILL.md:101`「`<中文描述>` 同第 4 步 docs 目录的描述」—— 步骤从 7 扩到 8 步后，docs 目录创建顺延为第 5 步，这处引用变成自指 worktree 创建本身。**

典型的「**顺延了步号，却漏了 diff 之外的正文引用**」。改为「第 5 步」。

顺带修了同轮判 45–65 分未上报的一条：`<主分支>` 在第 1 步就被用上，探测方法却定义在第 4 步展开小节。加一句**指针**（只指路、不复述命令，避免双写漂移）。

### 第 2 轮：1 条 finding（置信 78，已修）

**关闭动词正则只有右边界，没有左边界。**

第 1 轮我给数字加了右边界 `([^0-9]|$)`（挡「查 `#11` 命中 `#114`」），但动词侧写成 `(clos|fix|resolv)[a-z]*` 一把抓，于是：

```
$ echo "still unresolved #11" | grep -iE '(clos|fix|resolv)[a-z]* #11([^0-9]|$)'   # 命中
$ echo "not fixing #11 yet"   | grep -iE '(clos|fix|resolv)[a-z]* #11([^0-9]|$)'   # 命中
```

**把「还没修」报成「已经修完了」** —— 同一类漏洞的另一侧，我只堵了一侧。

置信 78 在 80 阈值**下方**、按 rubric 本可丢弃；仍然修，因为代价是一次误报式停机，而修它只要改一行。

**修法不是简单加左边界**：先试 `(^|[^a-z])(clos|fix|resolv)[a-z]*`，实测 `unresolved` / `AlsoCloses` 挡住了，**`not fixing` 仍然命中** —— 因为 `fix[a-z]*` 会吃掉 `fixing`。根因是 `[a-z]*` 太宽。最终按 **GitHub 的真实关闭关键字清单枚举**（close/closes/closed、fix/fixes/fixed、resolve/resolves/resolved，**没有进行时**）：

```
(^|[^a-z])(close[sd]?|fix(es|ed)?|resolve[sd]?) #<N>([^0-9]|$)
```

### 验证：拿文件里的真串跑，不是拿「我以为写进去的」跑

第一次验证**自己翻了车**：用 `grep -o` 抠正则时模式没匹配上，变量成了空串，而空正则匹配一切 —— 输出「全部命中」，看起来像结论，其实什么都没测。改用 python 抠出后重跑：

- 文件里两处 `--grep` 正则**逐字一致**，且与预期逐字相同；
- 6 条反例全落空（`unresolved` / `not fixing` / `AlsoCloses` / `closing` / `#114` / `reopens`）；
- 12 条正例全命中（九种关键字词形 + 行首 `- ` 前缀 + 句末句点 + **多行 body 里的 `Closes #11`**）；
- 真仓库回归：`#91` 命中 `735c04c`，`#114` / `#116` 为空（确认本轮两条 issue 未被远端做过）。

**这次翻车本身值得记**：验证脚本自己出错时，最危险的形态不是报错，而是**输出一份看起来全绿的结果**。

### 三个角度的最终结论

| 角度 | 结论 |
| --- | --- |
| ① 契约与装配 | **clean** —— 独立重数 8 处「第 N 步」引用全部自洽；核对新指针确指向「探测主分支」那一条；`state`/`stateReason` 与上一 commit 的实现及单测逐字对得上 |
| ② 缺陷定向扫描 | 上述正则 finding；其余 clean —— 实测确认 `git ls-tree` 在 `docs/` 不存在时返回空不报错、`--remotes=origin --not <主分支>` 的在途语义成立、选项 flag 放在 `--not` 之后仍被正确解析 |
| ③ 项目规范合规 | **clean** —— 全仓扫描确认 `skills/` 与 `GLOBAL_AGENTS.md` 中**无任何指向 `/start` 内部步骤号的外部引用**；新增 schema 说明与 `scripts/platform_issue.md` 一致且带指针，不构成双写 |

## 开发单元 3 —— 宪法补撞车决策路径（`GLOBAL_AGENTS.md`）

### 元信息

- **档位**：默认档，角度 ①②③，**主会话直接委派**（当时误判 orchestrator 不可用，见单元 2 元信息的事后修正）。**事后已用 orchestrator 对同一份 diff 复核过一遍，结论一致为 clean**，并多出一条 55 分观察（「先盘点…再按下表取舍并请人类确认」的动作顺序略模糊，<80 丢弃）
- **闸 A（运行验证）**：纯规则文本，无可运行单元 → N/A；以 `check-refs` + 预算实测代偿
- **迭代轮数**：2 轮（第 1 轮 2 条 finding → 修 → 第 2 轮 clean），**收敛**
- **风险定级**：本文件**每会话全文常驻注入、影响所有项目与 CC / Codex 两端**，故给三个角度都配了攻击式专项

### 第 1 轮：①③ clean，② 报 2 条（均已修）

**Finding 1（置信 85）：三行取舍表不穷尽，且分类判据缺失。**

要害不在「少一行」，而在**分类轴只有「谁更全面」一根**：agent 遇到「远端更全但有 bug」时会归进第一行、直接弃己方，**去采纳一个有缺陷的实现** —— 而条文没有任何一处要求先验证远端实现真的能用。

修复（表格后新增一句，同时给兜底与前置条件）：

> **判不准归哪一行、或情形落在表外**（远端只做了一半、两边都不完整）→ 按「各有独有价值」那行走，它最保守、不丢任何一边。**「更全面」不等于「更对」**：弃己方之前先核实远端实现真的能用，别因为它覆盖得全就默认它是对的。

**Finding 2（置信 80）：「打备份 tag」不可执行。**

没写命令、没写命名、没写时机，而本仓其实**已有既定约定**。一个不经 `/rebase` / `/finish`、直接读宪法触发本条的 agent 不会去 grep 别的 skill，各轮 tag 命名必然发散，事后无法按统一模式检索 —— 而这条要求的全部价值就在「事后翻得到」。

修复：把命令与出处写进条文 —— `git tag backup/<分支名>-$(date +%Y%m%d-%H%M)`，与 `/rebase` / `/finish` 同一约定。

### 第 2 轮：clean（②① 双角度复审）

- **Finding 1 已消除**：② 确认新句真的堵住了那条路径 —— 面对「远端更全但有 bug」，**「核实」这一环会先失败，于是走第一行的前提不成立，自然退到第二 / 三行**。「怎么算核实过」确实没给可操作标准，但与本文件其它判断性条款（「实测结论」「代价高于重写」）的留白程度相当，② 判 <80 丢弃。
- **Finding 2 已消除**：两方独立核对，新写的命令与 `skills/finish/references/worktree-finish.md:20` **逐字一致**（占位符 `<分支名>`、时间格式 `%Y%m%d-%H%M` 都相同）。`skills/rebase/SKILL.md:77` 用英文占位符 `<branch-name>`，是**该文件本就存在**的差异、非本轮引入，两方均判 <80。
- **新句没有架空表格第一行**（这是我最担心的反向偏差，专门让 ① 攻）：它是前置校验而非否定，「已核实、确实更全面」时第一行照常成立；且兜底句已给出「不确定就不选第一行」的出路，不构成机制性架空。
- **没有可被援引的后门措辞**：① 双向核过 —— 既没有能被读成「远端做过了所以我可以自行放弃人类交代的任务」的独立授权语，也没有能被读成「因为要核实所以可以无限期不决定」的拖延许可。
- **前向引用已闭合**：`/start` 里那句「判据在宪法『执行』段的停机义务里」与本条首尾呼应，② 回查确认不是幽灵引用。

### 指令面预算（实测）

| | 字符 | 说明 |
| --- | --- | --- |
| `GLOBAL_AGENTS.md`（**常驻**） | 8,302 → 8,965（**+663**） | 含第 1 轮 470 + 修 finding 追加 193 |
| `skills/start/SKILL.md`（懒加载） | 5,381 → 8,404（**+3,023**） | **是 PLAN 估值的 2.5 倍**，见 SUMMARY 局限性 |
| `skills/triage/SKILL.md`（懒加载） | +34 | |
| 总指令面 | +2.0% | |

`check-refs`：无失效引用 ✅
