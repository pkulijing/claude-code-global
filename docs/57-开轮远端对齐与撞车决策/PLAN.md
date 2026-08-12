# PLAN · round 57 —— 开轮远端对齐与撞车决策

一次事故的两半：**#114 管撞车发生前（`/start` 开轮时拦住）**，**#116 管撞车已经发生（怎么取舍）**。

## 〇、先实证：issue 正文里的技术断言逐条核过

按 `/start`「外部行为断言先实证」，动笔前把 #114 正文里的 git 断言全跑了一遍真沙盘。**推翻一条、修正一条、坐实两条。**

### 0.1 ❌ 推翻：`--grep "Closes #<N>"` 是子串匹配，会误命中

issue 正文给的命令 `git log origin/master --grep "Closes #<N>" --oneline` **有 bug**：`--grep` 是正则子串匹配，**查 #11 会命中 `Closes #114`**。放进 skill 就是「开轮时被一条根本无关的 issue 拦住」，且越是小号 issue 越容易撞。

复现（沙盘 `git init`，两个空 commit）：

```bash
git commit --allow-empty -m "feat: 甲

Closes #11"
git commit --allow-empty -m "feat: 乙

Closes #114"
git log --grep "Closes #11" --oneline
# → e971c32 feat: 乙   ← 误命中
#   e2c821a feat: 甲
```

**改用**（加数字边界 + 覆盖 GitHub 认的全部关闭动词 + 大小写不敏感）：

```bash
git log <ref> -i -E --grep "(clos|fix|resolv)[a-z]* #<N>([^0-9]|$)" --oneline
```

实测：`#11` 只命中 `Closes #11` 与 `fixes #11`，**不再命中 `Closes #114`**；`#200` 正确命中 `Resolves #200`。

### 0.2 ✅ 坐实：`git ls-tree` 第四源可用

```bash
git ls-tree --name-only origin/master docs/
# → docs/53-review成本与思考深度调优 / docs/54-... / docs/55-... / docs/DEVTREE.md
```

### 0.3 ✅ 坐实：round 55 的撞车确实可被这条检查拦下

```bash
git log origin/master -i -E --grep "(clos|fix|resolv)[a-z]* #91([^0-9]|$)" \
  --format="%h %ad %s" --date=short
# → 735c04c 2026-08-02 fix(review-loop): 给降级链定义「什么才算失败」…
```

即：round 55 开轮时若跑这条，**当场就能看见 #91 已被 6 天前的 commit 关闭**。

### 0.4 ➕ 补一条 issue 没想到的：在途（未合入）也要看

`git log origin/<主分支>` 只看**已合入**。但本仓的 `/routine-dev` 每周开 PR **却不自动合**，于是存在一整类撞车：**远端分支上已经做完了、PR 还开着、issue 也还 open**。这类用 `state` 查不出、用 origin/master 也 grep 不到。

实测可用（`--not <主分支>` 排除已合入的）：

```bash
git log --remotes=origin --not origin/<主分支> -i -E --grep "…" --oneline
```

### 0.5 ❗ 发现：helper 目前**根本不返回 issue 状态**

`platform_issue.py` 的 `normalize_issue()`（`scripts/platform_issue.py:130`）只吐 `number` / `title` / `body` / `url` / `labels`，**没有 `state`**；`build_issue_view_cmd()`（同文件 `:397`）向 `gh` 请求的字段里也没有。

所以「issue 是否已关闭」**当前拿不到**，必须动 helper。实测 `gh` 侧字段确实存在且好用：

```bash
gh issue view 91  --json number,state,stateReason  # → {"state":"CLOSED","stateReason":"COMPLETED"}
gh issue view 114 --json number,state,stateReason  # → {"state":"OPEN","stateReason":""}
```

**GitLab 侧未实测**（本机没装 `glab`）—— 归一化据此设计成不依赖对 GitLab 词形的猜测，见 §2.2。

## 一、总体设计

三处改动，一条主线：**让「远端已经做过了」在开轮那一刻就可见**。

| # | 改哪 | 为什么 |
| --- | --- | --- |
| A | `scripts/platform_issue.py` + 单测 | 让 `issue-view` 吐出 `state` —— 唯一**不依赖 commit message 约定**的权威信号 |
| B | `skills/start/SKILL.md` | 新增「远端对齐」为通用流程第 1 步；轮次编号补第四、第五源 |
| C | `GLOBAL_AGENTS.md` | 撞车**已经发生**后的取舍判据（#116） |

## 二、改动 A：helper 吐出 issue 状态

### 2.1 为什么非改 helper 不可（而不是只用 git grep）

`git log --grep "Closes #N"` 依赖**提交信息写了 `Closes #N`**。本仓 `/finish` 确实写，但 **`/start` 是全局 skill**，要在任何项目里跑 —— 别的项目未必有这个约定，那里 grep 恒为空。

而 `state` 是平台的权威事实，还能覆盖三类 grep 看不见的关闭：人工手动关、PR 用别的措辞关、**关成 `wontfix`（`NOT_PLANNED`）**。最后一类尤其重要 —— 那说明**有人决定过不做**，跟「已经做完了」是完全不同的处理。

两个信号是互补的：`state` 回答**「还该不该做」**，git grep 回答**「谁做的、什么时候、哪个 commit」**（人类拍板要的证据）。

### 2.2 具体改法

**`build_issue_view_cmd()`**：GitHub 分支的 `--json` 字段表加 `state,stateReason`（GitLab 的 `-F json` 是整对象，无需改）。
**`build_issue_list_cmd()`**：GitHub 分支加 `state`，让 `/triage` 那条路上的 `state` 也是真值而非默认值。

**`normalize_issue()`**：新增两个字段，**两端归一**：

```python
out["state"] = "closed" if str(raw.get("state") or "").lower() == "closed" else "open"
out["stateReason"] = raw.get("stateReason") or ""   # GitHub 独有，GitLab 恒为 ""
```

三个设计点：

1. **归一成只有 `open` / `closed` 两个值。** GitHub 是 `OPEN` / `CLOSED`（大写，实测），GitLab 是 `opened` / `closed`（**未实测**）。若原样透传，消费方写 `state == "open"` 会在 GitLab 端恒假 —— 这正是 `normalize_issue` 存在的意义，必须在此收口。
2. **判据挂在 `closed` 而不是 `open` 上。** 两端表示「关闭」都是 `closed` 这一个词（这是唯一需要赌的点，且 GitLab API 文档亦如此），而「打开」两端词形不同（`OPEN` vs `opened`）。挂在词形一致的那一侧，未实测的一端才不会判错。
3. **`stateReason` 平台不对称，如实记在文档里**，不假装 GitLab 也有。

**兼容性**：纯新增字段，现有消费方（`/triage` / `/quick` / `/sync-project-config` / `/routine-dev`）读的字段一个没动。

### 2.3 TDD

`normalize_issue` / `build_issue_view_cmd` 都是纯函数，**先写测试再改实现**。

> **执行中修正（review 推翻了原计划的落点）**：原计划新建 `docs/57-*/test_platform_issue.py`，沿用 round 52 `test_context_budget.py` 的先例。实际这么做了（19 例，先红后绿），但提交前 review 查出 `scripts/platform_issue.py` **自带一套 `cmd_self_test()`**（`--self-test`），里面硬编码着旧 schema 的期望值 —— 改了 schema 没同步它，`--self-test` 直接红（exit 1、7 条 FAIL）。
>
> 更要紧的是它才是**被文档承认的门禁**：`skills/routine-dev/SKILL.md:186` 明写「`scripts/platform_issue.py` → `python3 scripts/platform_issue.py --self-test`」。留两套测试意味着**新增的 state 逻辑不在那道门禁覆盖内** —— 将来 routine 改这个脚本，门禁绿着而 state 归一已经坏了，正是本仓最忌的「静默失效的门禁」。
>
> **故改为：把用例并进 `cmd_self_test()`，删掉独立文件。** 两条依据：① 单一真源、不双写；② 宪法「写代码要像周围的代码」—— 这个文件的既有惯例就是内联 self-test（round 52 那个先例成立是因为 `context_budget.py` 根本没有内联 self-test）。代价：失去 `unittest` 的命名用例与 `subTest`，换成 `failures.append` 惯例。

| 用例 | 输入 | 期望 |
| --- | --- | --- |
| GitHub 已关闭 | `{"state":"CLOSED","stateReason":"COMPLETED"}` | `state="closed"`, `stateReason="COMPLETED"` |
| GitHub 未关闭 | `{"state":"OPEN"}` | `state="open"`, `stateReason=""` |
| GitHub wontfix | `{"state":"CLOSED","stateReason":"NOT_PLANNED"}` | `state="closed"`, `stateReason="NOT_PLANNED"` |
| GitLab 已关闭 | `{"state":"closed"}` | `state="closed"` |
| GitLab 未关闭 | `{"state":"opened"}` | **`state="open"`** ← 归一的核心断言 |
| 字段缺失（`issue-list` 老路径） | `{}` | `state="open"`，不抛异常 |
| 命令构造 | `build_issue_view_cmd(GITHUB, 3)` | 字段串含 `state` 与 `stateReason` |
| 命令构造·GitLab 不变 | `build_issue_view_cmd(GITLAB, 3)` | 与改动前逐字一致 |
| 既有字段不回归 | GitHub 典型 raw | `number/title/body/url/labels` 全部照旧 |

**环境无关**：全是纯函数入参，不发网络、不读 `$HOME`、不调 `gh`/`glab` —— 任何机器上逐字同结论。

## 三、改动 B：`/start` 的远端对齐

### 3.1 通用流程插入新的第 1 步（原 1～7 顺延为 2～8）

为什么必须排在最前：① 轮次编号要用远端信号；② **撞车检查必须在建 worktree / 建 docs 之前** —— 否则拦住了也已经落了一个分支和一个目录要清。

顺延带来的内部引用同步修改：「（通用流程第 3 步展开）」→ 第 4 步、「（通用流程第 6 步展开）」→ 第 7 步。

### 3.2 新第 1 步「远端对齐」内容

```
1. 远端对齐（多设备 / 云端 routine 并行下，本地信号必然滞后）
   a. git fetch origin —— 只更新 remote-tracking，不碰工作区
   b. issue 驱动时：拉 issue 详情（这一次调用即「issue 驱动分支」第 1 步那一次，不要调两遍），
      读 state；再 grep 关闭它的 commit（已合入 / 在途各一条）
   c. 任一命中 → 停下报告，附证据，列三个选项等人类拍板
```

**命中后停下报告的格式**（附证据，让人类一眼能判）：

```
⚠ #<N> 看起来已经被做过了：
  - issue 状态：closed（COMPLETED，2026-08-01）
  - 关闭它的 commit：735c04c 2026-08-02 fix(review-loop): …（已在 origin/master）
选项：① 不做了（本轮取消）② 只补真增量（说明差在哪）③ 远端做得不对，重做（说明哪不对）
```

三个选项**照抄 issue 原文**，不自作主张替人类删减。

**`stateReason == "NOT_PLANNED"` 单独提示**：那不是「做完了」，是「有人决定不做」，报告里必须写清，因为处理方向完全相反。

### 3.3 轮次编号：三源 → 五源

| 源 | 命令 | 覆盖 |
| --- | --- | --- |
| ①②③ 现有 | 本树 `docs/` / 本地 `round*` 分支 / 其它 worktree | 本机 |
| ④ **新增** | `git ls-tree --name-only origin/<主分支> docs/` | 远端**已合入** |
| ⑤ **新增** | `git branch -r --list 'origin/round*'` | 远端**在途** |

⑤ 是 ② 的远端对应物（② 只看得见本机分支），与 ④ 同吃一次 fetch，零额外成本。沿用既有的「解析失败一律跳过、不报错」。

### 3.4 降级：三条独立失败路径，一条都不许阻断开轮

| 失败 | 处理 |
| --- | --- |
| 无 `origin` remote（纯本地仓） | 跳过整个远端对齐，一行提示，继续 |
| `git fetch` 失败（离线 / 无权限） | 跳过④⑤与 commit grep，**明确打印**「远端对齐已跳过：<原因>；轮次编号与撞车检查仅基于本地信号」，继续 |
| helper 拉 issue 失败 | 按现有行为，不因新增的 `state` 检查而变严 |

`state` 检查走平台 API、`fetch` 走 git，**两者互相独立** —— 一个挂了另一个照跑。

**不做**：#114 明确「只改 `/start`，不动 `/finish`」。（现状记录：`/finish` 也不 fetch，round 55 是人工跑的 —— 属另一条 issue 的范围，本轮不夹带。）

### 3.5 无人值守？—— 核查过，不适用

「停下报告等人类」在无人在环的会话里会永久挂起。**已核实 `/start` 不被任何 routine 调用**：`/routine-dev` 明写「形态上对标 `/quick` 而非 `/start`」（`skills/routine-dev/SKILL.md:11`），`/routine-slim` 同理。故本步停机安全，**不需要**为它加无人值守分岔。

## 四、改动 C：宪法补撞车决策路径（#116）

### 4.1 落点

`GLOBAL_AGENTS.md` §需求生命周期 ·「执行」段，紧接**「计划假设被证伪时的停机义务」**之后作为并列 bullet —— issue 原文就把它定位成那条的**具体子类**，物理相邻能让读者看见「都是停机、触发条件不同」。

与既有那条的分工（**刻意不重复**，round 55 的头号教训就是双写漂移）：

- 既有：**计划的技术假设**不成立 → 停机；
- 新增：**交付物本身**已被远端做掉 → 同样停机，但**取舍表不一样**。

### 4.2 拟增文本

> - **交付物与远端已合入的实现撞车，同属停机义务**（触发的不是技术假设失效，而是「这事已经被别人做完了」）：先逐条盘点「远端有 / 己方有 / 双方都有」，再按下表取舍并请人类确认：
>
>   | 情形 | 处理 |
>   | --- | --- |
>   | 远端已覆盖且更全面 | **弃己方**，只在远端基础上补真增量 |
>   | 各有独有价值 | 把己方增量**重写**到远端版本之上，**别硬 rebase** —— 同段落双方都改过，解冲突 + 手工去重 + 改轮次编号 + 重做 DEVTREE 的代价高于重写 |
>   | 己方更全面 | 保留己方，但必须逐条说明远端版本的哪些点已被吸收 |
>
>   **弃掉的工作必须打备份 tag，并在 `SUMMARY.md` 写明弃因** —— 否则后来者翻到那段历史会误以为它是**被否决的设计**（真实代价：一次 review 里 reviewer 真的翻出了弃用分支，花力气评估己方是否在「重蹈已放弃的设计」）。源头防线是 `/start` 的开轮远端对齐，本条管的是它没拦住时怎么办。

### 4.3 两个措辞决定

**用表格而非散文**（多花约 160 字符）：这是个三分支取舍，压成散文后三条路会挤在一句里，正是最容易读漏的形态；宪法既有先例（Co-authored-by trailer 表）。round 55 §3.5 恰好留了个悬案 ——「表格比散文更难读漏，但无实证」；本条**主动选表格**，把那个悬案落到一个可观察的位置。

**不复述无人值守例外**：宪法既有停机条款已写「（无人在环的会话无此选项，按 skill 的降级 + 留痕走）」，同一段落内不再重复一遍 —— 常驻指令面每一个字都在每个会话里付费。

### 4.4 预算

`GLOBAL_AGENTS.md` 是**常驻**（8,302 字符 / ~6,849 token，每会话全文注入）。拟增约 600 字符 ≈ 常驻面 +3.9%、总指令面 +0.35%。`skills/start/SKILL.md` 是懒加载，约 +1,200 字符。收尾时用 `context_budget.py measure` / `delta --since` 实测记入 `SUMMARY.md`。

## 五、验证

| 闸 | 做法 |
| --- | --- |
| 单测（改动 A） | `python3 scripts/platform_issue.py --self-test`（该脚本的**唯一**门禁，`routine-dev` SKILL 亦指向它） |
| 真机冒烟（改动 A） | `platform_issue.py issue-view 91` 应吐 `"state": "closed"` / `"stateReason": "COMPLETED"`；`issue-view 114` 吐 `"open"` |
| 沙盘回归（改动 B 的 grep） | §0.1 的沙盘再跑一遍，确认 `#11` 不命中 `#114` |
| 机械验证（改动 B/C） | `context_budget.py check-refs` 无失效引用 |
| 端到端 | 本轮**自己就是**第一个用例：开轮时已手动跑完 fetch + 双 grep + 五源编号，结论「#114/#116 均未被远端做过、N=56」 |
| 提交前 | 每次 commit 前 `/review-loop`（改的是 skill / 宪法这类指令文件，**明令不可跳过**） |

## 六、文档同步（schema 一改就得跟的地方）

- `scripts/platform_issue.md` —— helper 文档，schema 真源，补 `state` / `stateReason`；
- `skills/start/SKILL.md` —— 内联的 schema json 块补两个字段；
- `skills/triage/SKILL.md:29` —— 那句枚举了字段名，同步补，避免 drift。

## 七、执行顺序

1. 写单测（红）→ 改 `platform_issue.py`（绿）→ 真机冒烟 → **commit 1**（含 §六 的 helper 文档）
2. 改 `skills/start/SKILL.md`（远端对齐 + 五源 + 顺延编号 + schema 块）→ **commit 2**
3. 改 `GLOBAL_AGENTS.md` → 跑 `check-refs` + 预算 → **commit 3**
4. `/finish`：`SUMMARY.md` + DEVTREE + `Closes #114` / `Closes #116`

每个 commit 前自动 `/review-loop`。

## 八、明确不做

- 不改 `/finish`（#114 明令）；不给 `/finish` 加 fetch。
- 不动 `/routine-dev` / `/routine-slim` 的安全边界与 `agents/`。
- 不改 `/quick`（它也吃 issue，但轻量流不该背这套检查；如需要另起 issue）。
- 不实测 GitLab 端（本机无 `glab`）—— 归一化按「只赌 `closed` 一个词」设计以降低风险，局限如实写进 `SUMMARY.md`。
