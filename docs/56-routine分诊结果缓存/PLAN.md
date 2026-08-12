# PLAN —— routine-dev 分诊缓存（`auto:skip`）

## 零、先做的实证：三个候选方向里有两个当场出局

按「外部行为断言先实证」，动笔设计前先核了 issue 正文里三个候选方向所依赖的技术假设。**结论是方向 A、B 都不成立**，原方案表里剩下的 C 又与硬约束 1 冲突，所以本轮必须引入一个 issue 里没列的方向。

### E1 · 给 **issue** 打 label 不在 `ff-merge` 的触发面上（方案成立的前提）

`.github/workflows/ff-merge.yml:12-17` 的 `on:` 块只订阅两个事件：

```yaml
on:
  pull_request_target:
    types: [labeled]
  issue_comment:
    types: [created]
```

`pull_request_target.labeled` **只在 PR 被打 label 时触发**；给 issue 打 label 发出的是 `issues.labeled`，不在订阅列表里。准入闸（同文件 `if:`）进一步要求 `github.event.label.name == 'ff-merge'`。

→ **routine 给 issue 打 `auto:skip`，物理上够不到那条自动合入的路。** 这是整个方案能成立的前提，先证它。

### E2 · 方向 A（留机器评论存时间戳）出局：撞 SKILL 的硬规则

`skills/routine-dev/SKILL.md`「明确不做」写着：**不发任何评论 —— 只通过「开 PR」和「编辑 PR 描述」说话**。推导在 `references/security-boundary.md` §1：`ff-merge.yml` 订阅 `issue_comment.created`，routine **从不产生评论**这条触发路径就物理上够不着。

诚然 `if:` 里 `github.event.issue.pull_request != null` 会拦下 issue 评论，但这道规则的价值恰恰在于**不依赖 `if` 判对** —— 为了省一点 token 去换掉一道机制性防线，不划算。**方向 A 否决。**

### E3 · 方向 B（读 timeline 的 `labeled` 事件时间）出局：云端主形态大概率取不到

- 云端 raw GitHub REST API 一律 403（`playbooks/cloud-routine.md` 能力矩阵），`gh` 未安装 —— 所以 `gh api .../timeline` 只有本机能跑，而**本机是辅助形态、云端才是主形态**。
- 云端只能走内置 GitHub MCP，其工具列表**以当次会话为准、不凭记忆猜**。公开可查的 mainline `github/github-mcp-server` 有 label 类工具（`add_labels_to_issue` / `remove_label_from_issue`），**timeline / issue 事件的暴露只见到 feature request**。

→ 方向 B 在云端极可能永远取不到时间戳，按 issue 里写的「取不到就退化成照常完整分诊」，等于**这个优化在主形态下永远不生效**。**方向 B 否决。**

### E4 · 本机 label 增删能力已实测存在

`gh issue edit --help`：`--add-label name` / `--remove-label name`，**增量语义**（不是全量替换），可重复传。`glab` 本机未安装 → GitLab 侧按 helper 既有惯例做成纯函数 + 沙盘桩测，并在契约文档标注未实测（先例：`issue-comment` 的 GitLab 输出 schema）。

### E5 · 落点无在途 PR 冲突

`gh pr list --state open` 为空，本轮落点不会撞车。

---

## 一、方案：`auto:skip` label + GitHub Actions 事件驱动复活

既然「时间戳存哪儿」的三条路都被堵死，就**别再存时间戳** —— 把「issue 被动过就复活」这件事交给 GitHub 的事件系统本身：

| 角色 | 谁做 | 动作 |
| --- | --- | --- |
| **打标** | routine（Step 1.2 之后） | 给自动通道判掉的 issue 加 `auto:skip` |
| **读标** | routine（Step 1.1，不读正文） | 带 `auto:skip` 的直接排除 |
| **复活** | **新 workflow**（`issues.edited` / `issue_comment.created` / `issues.reopened`） | 自动摘掉 `auto:skip` |

这样 routine 侧只需要**一个写能力**（加 label），不需要读时间戳、不需要 timeline、不需要发评论。语义上与用户拍板的「按更新时间自动复活」等价，且更精确 —— 复活由「真有人动了这条 issue」触发，而不是由一个可能被别的动作顺带推高的时间戳触发。

### 为什么不会自触发循环

label 变更发出的是 `issues.labeled` / `unlabeled`，**不是 `edited`**（`edited` 只对 title / body 编辑触发）；且 `GITHUB_TOKEN` 产生的事件按 GitHub 规则不再触发新的 workflow run。routine 打标 → 不触发复活 workflow；workflow 摘标 → 不触发自己。

### 新 workflow 的安全性质（对齐 `ff-merge.yml` 那段注释的标准）

- 用 `issues` / `issue_comment` 触发，**不是 `pull_request_target`** —— 不存在「在特权上下文里跑 PR 代码」这类漏洞形态；
- **不 checkout 仓库、不执行工作区里的任何文件**，只调一次 `gh issue edit --remove-label`；
- `permissions:` 只给 `issues: write`（显式声明后未列出的 scope 一律 none）；
- 攻击面评估：公开仓里任何人评论任何 issue 都能让它摘掉 `auto:skip`，**后果上限是「该 issue 回到今天的行为」（重新被完整分诊一次）** —— 不构成提权，只是放弃一次优化。

### 硬约束逐条兑现

| 约束 | 怎么兑现 |
| --- | --- |
| 1. 不能误判一次即永久出局 | 复活 workflow；人手动摘 label 也照常有效 |
| 2. `auto:take` 压过 skip | Step 1.1 表里标记通道**不排除** `auto:skip`；且**只对自动通道打标**，带 `auto:take` 的从不打 |
| 3. 不与 `wontfix` 混淆 | label description 写明「issue 仍 open、人照常可做；被人动过会自动摘掉」；`wontfix` 仍是 closed 归档 |
| 4. `--dry-run` 不打 label | 打标动作写在 Step 1.2 之后、Step 2 之前，`--dry-run` 明确跳过（它本来就「到 Step 2 为止」，此处加一句显式禁令） |

---

## 二、落点清单（7 处）

| # | 文件 | 改什么 |
| --- | --- | --- |
| 1 | `scripts/platform_issue.py` | 新增 `issue-label-add` / `issue-label-remove` 子命令（双轨）+ 沙盘单测 |
| 2 | `scripts/platform_issue.md` | 补两条子命令的契约语义 + GitLab 侧未实测标注 |
| 3 | `.github/labels.yml` | 新增 `auto:skip` label 定义 |
| 4 | `.github/workflows/auto-skip-reset.yml` | **新建**：复活 workflow |
| 5 | `skills/routine-dev/SKILL.md` | Step 1.1 加一行、新增 Step 1.3 打标、分岔契约表加一行、Step 4 跳过段、「明确不做」里把「不打 label」精确化 |
| 6 | `skills/routine-dev/references/security-boundary.md` | §1 补一小节：为什么打 issue label 不破坏那道防线（E1 的推导 + 新 workflow 的性质） |
| 7 | `skills/triage/SKILL.md` + 本仓 `CLAUDE.md`（+ `README.md` 若列了 label） | 让人看得见 `auto:skip`：triage 表标注一列；仓库文档补一句 |

---

## 三、TDD：先写测试

`platform_issue.py` 的 argv 构造是纯函数（`build_*` 系列已有此惯例），**输入 X → 输出 Y 写得清楚，先写测试**。在 `cmd_self_test()` 里加以下用例（先红后绿）：

| 用例 | 期望 argv |
| --- | --- |
| GitHub 加一个 label | `["gh","issue","edit","7","--add-label","auto:skip"]` |
| GitHub 加多个 label | 重复 `--add-label`（**不拼逗号** —— label 名里出现逗号会被拆错） |
| GitHub 删 label | `["gh","issue","edit","7","--remove-label","auto:skip"]` |
| 带 `--repo` | 末尾追加 `["--repo","owner/name"]` |
| GitLab 加 / 删 | `["glab","issue","update","7","--label","auto:skip"]` / `--unlabel`（**标注未实测**） |
| 空 label 列表 | argparse 层拒绝（`required=True` + `action="append"`） |

另加一条**沙盘用例**（桩掉 `gh`、断言真实 argv 落地），与既有 `_sandbox_issue_comment()` 同形 —— 这一条测的是「正文 / 参数不经 shell」这条既有纪律。

workflow 的行为**无法本地单测**（要真实 GitHub 事件），处理见第五节。

---

## 四、实施顺序（3 个 commit）

1. **helper 层**：单测（红）→ `issue-label-add` / `issue-label-remove` 实现（绿）→ `scripts/platform_issue.md` 契约。
2. **平台层**：`.github/labels.yml` 加 `auto:skip` + 新建复活 workflow + `security-boundary.md` 补推导。
3. **指令层**：`skills/routine-dev/SKILL.md` 的五处改动 + `/triage` 标注 + 仓库文档。

每个 commit 前照常走 `/review-loop`（本轮落点全是指令规则文件与可执行面，**宪法明令不得跳过**）。

---

## 五、验证与遗留

- **本地可验**：`python3 scripts/platform_issue.py --self-test` 全绿。
- **本地不可验、必须合入后做一次真实验证**：`on: issues` 类 workflow **只有默认分支上的版本才会被触发**，所以复活链路在 PR 合入 master 之前跑不起来。合入后手工验一次：
  1. 用新子命令给一条测试 issue 打 `auto:skip`；
  2. 编辑该 issue 正文；
  3. 观察 label 是否被自动摘掉（Actions 里应有一次 run）。
  这条写进 SUMMARY 的「后续 TODO」，`/finish` 时不当作已完成。
- **云端能力仍未实测**：云端内置 GitHub MCP 是否有 label 写工具，**只能等下一次真实 routine 运行才知道**。故 SKILL 里的打标动作写成「探测当次会话可见的 label 类工具 → 找不到就跳过打标、不阻断」，并把这一分岔写进无人值守契约表。最坏情况是优化在云端不生效、行为回退到今天，不会把 routine 跑挂。
- **收尾动作**：合入后跑 `python3 $HOME/.claude/scripts/platform_issue.py label-sync-from-file .github/labels.yml`，否则新 label 在远端不存在、打不上。

---

## 六、待你确认的一项

**要不要接受新增 `.github/workflows/auto-skip-reset.yml` 这个 workflow？**

这是本方案唯一「issue 正文里没提过」的部分。理由是 A / B 两条存时间戳的路都被实证堵死（第零节），而你选的是「自动复活」，事件驱动是剩下唯一能兑现它的路。

不接受的话，只能退回方向 C（只打标、不自动复活，靠 `auto:take` 或人工摘 label），**与硬约束 1 冲突** —— 需要你改这条约束才能走。
