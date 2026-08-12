# REVIEW · round 56

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
2. **结构决定**：把 19 个 unittest 用例并进 `cmd_self_test()`（新增 `state_cases` / `reason_cases` 两组），删掉独立文件 `docs/56-*/test_platform_issue.py`。

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
