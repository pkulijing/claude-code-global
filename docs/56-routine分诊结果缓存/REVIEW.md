# REVIEW 留痕 —— round 56

## 第 1 次（commit 1 前）：helper 的 `issue-label-add` / `issue-label-remove`

- **档位**：默认档（`review-orchestrator` ×1 + `code-reviewer` ×3，角度 ①②③）。改动是 argv 构造 + 子进程调用，无并发 / 状态机 / 跨进程容错特征，不升重档。
- **闸 A 运行验证**：`python3 scripts/platform_issue.py --self-test` 通过（orchestrator 侧亦独立实跑一次）。
- **闸 B 结果**：**clean，无 finding**。
  - 角度①：`build_issue_label_cmd` 签名与全部调用点一致；子命令名在 `build_parser()` / `main()` handlers / 契约文档三处一致。
  - 角度②：`gh issue edit --add-label/--remove-label` 与 `glab issue update --label/--unlabel` 无 API 幻觉；错误处理与既有 `cmd_issue_comment` 同构；`--label required=True` 堵住空值边界。
  - 角度③：与 `GLOBAL_AGENTS.md` / 本仓 `CLAUDE.md` / `playbooks/python.md` 无冲突，风格与同文件既有惯例一致。
- **闸 C**：无 finding 落在已定设计前提（`auto:skip` 方案已由人拍板、GitLab 侧未实测、exit code 复用既有约定）上，无需追加前提。

**结论：一轮即收敛，放行。**

## 第 2 次（commit 2 前）：`auto:skip` label 定义 + 复活 workflow + 安全推导

- **档位**：**重档**（`code-reviewer` ×4 角度 ①②③④ + `code-reviewer-deep` ×1 角度 ⑤）。改的是 CI 事件订阅与安全边界，涉及触发条件、权限模型、会不会自触发循环这类时序判断，属「审浅了会漏真问题」的一类。
- **闸 A 运行验证**：workflow 的行为要合入默认分支才跑得起来，本地判 N/A；能验的都验了 —— YAML 可解析、`.github/labels.yml` 经仓库自己的 `parse_labels_yml` 解析出新条目、`python3 scripts/platform_issue.py --self-test` 仍绿。
- **角度 ①②③④ 全 clean**，并逐条核实了本轮提出的 6 项技术断言全部成立（`pull_request_target.labeled` 只对 PR 触发、无自触发 / 互触发、`if` 条件在两种 payload 下都取得到 labels、`issues: write` 恰好够用不过量、label 颜色与 description 合规、run 步骤没把任何用户可控文本插进 shell）。
- **角度 ⑤ 命中 2 条**，都不是本次三个文件的缺陷，而是**对下一个 commit（Step 1.3 打标逻辑）的设计级约束**：

### Finding 1（置信 88）· 「读正文」到「打标」之间的窗口会静默吞掉人类的补救编辑

`if:` 判的是 webhook 投递时冻结的 payload 快照。序列：T0 routine 批量读完全部 issue 正文 → T0+3min 人类编辑某条把正文补清楚（此刻 issue 上**还没有** `auto:skip`，复活 workflow 的 `if` 判 false、不起 job）→ T0+8min Step 1.3 按**已作废的旧正文**打上 `auto:skip` → 该 issue 基于过期判断被缓存出局，而编辑的人并不知道自己那次编辑没算数。

**处置：不接受「缩小窗口」这种缓解，改为在 Step 1.3 里彻底堵掉** —— 打标前重新核对该 issue 的 `updatedAt` 是否已晚于本次运行读它时的快照，变了就不打标。锚点是两个都落在**同一次运行内**的时间戳，不需要任何持久化，也不依赖 timeline / 评论。为此 helper 的 `issue-list` 需要吐 `updatedAt`，并加一个 `--no-body` 让这次复核真的便宜（否则复核要把正文再读一遍，正是本轮要省的那笔）。见 commit 3。

### Finding 2（置信 80，低危自愈）· 评论风暴中排队的陈旧 run 可能多摘一次 label

`cancel-in-progress: false` 只取消 in-progress、不取消 pending，同 group 内 pending run 会被后来者顶替但保留首尾两条；拿着陈旧快照的那条出队后会把 routine 刚写回的 label 再摘一次。后果是缓存丢一次、下轮多花一次分诊，**下一轮自动写回，自愈**。

**处置：不改逻辑，补护栏注释。** 这条 job 的并发安全完全建立在「摘 label 幂等」上，故在文件头写明「往这个 job 加任何非幂等副作用都会破坏这条前提」，与 `ff-merge.yml` 里那条「别加执行工作区文件的步骤」同类。注释是纯机械补充，不再另起一轮复审。

**结论：本 commit 的三个文件闸 B 通过，放行；两条 finding 转为 commit 3 / 4 的设计输入。**

## 第 3 次（commit 3 前）：`updatedAt` 字段 + `issue-list --no-body`

Finding 1 的堵法落地：helper 吐 `updatedAt`，并加 `--no-body` 让「只要时间戳」的复核不必把正文再拉一遍。

- **档位**：默认档（`code-reviewer` ×3，角度 ①②③）。纯数据归一 + argv 构造，无并发 / 状态机特征。
- **闸 A 运行验证**：`--self-test` 全绿（先红后绿：新用例在实现前分别以 `TypeError` 与字段不符失败）；另对真实仓库跑 `issue-list --limit 3 --no-body`，返回不含 `body`、含 `updatedAt` 的结果。
- **闸 B 结果**：**clean**。三个角度均确认：现有消费方没有对 schema 做精确 key 集合匹配、也没有裸 `d["body"]` 硬取值，多一个键不破坏任何人；全文搜索无时间戳兜底逻辑；`gh_raw` 用例确实完全不含 `updatedAt` 键（而非显式 `None`），能真正抓住「误加兜底」的回归。
- **顺手修**：reviewer 提到但置信不足 80 未上报的一处 —— `build_issue_view_cmd` 的 docstring 还写着「默认字段集未动」，加了 `updatedAt` 之后这句已失真，改掉。纯注释修正，不另起复审。

**结论：一轮即收敛，放行。**

## 第 4 次（commit 4 前）：指令层 —— Step 1.3 与 `/triage` 一列

**本 commit 跑满了 `/review-loop` 的 2 轮自动上限，按规则留痕放行。** 两轮共 9 条 finding，**全部已修**，但第 3 轮确认复审**没有跑**（上限即停，不再往下烧）。人工核对的落点在 `/finish`。

- **档位**：重档（`code-reviewer` ×4 角度 ①②③④ + `code-reviewer-deep` ×1 角度 ⑤），两轮均未降档。
- **闸 A 运行验证**：纯指令规则文件，无可运行单元 → N/A；能机械验的都验了 —— `context_budget.py check-refs` 两轮均报「无失效引用」。

### 第 1 轮：4 条（全部来自角度 ⑤）

| # | 置信 | 问题 | 修法 |
| --- | --- | --- | --- |
| F1 | 92 | 复核时间戳的命令只给了本机写法，而 helper **在云端整个不可用**，云端恰是主运行形态 | 复核改成本机 / 云端两行；并显式定义取不到时 **fail-closed：放弃打标** |
| F2 | 88 | 1.3 要比对的快照，Step 1 从未承诺产出（前言只说拉 labels/title/body） | Step 1 前言加「最后更新时间」并要求留成本次运行的快照；**取不到就记「无快照」，不许拿当前时间填** |
| F3 | 85 | 复核只收窄窗口、不消灭窗口，但行文让人以为已闭合 | 显式声明残余窗口；规定复核紧邻打标循环之前做、一口气打完；写明**不要靠「打完再读一次」闭环**（`issue-label-add` 自己会 bump 时间戳，必然 100% 误报） |
| F4 | 80 | 「疑似已完成」这类**依据仓库现状**的判定被永久缓存 —— 对既有行为的实质降级 | 新增第四类不打标：**缓存的失效信号必须与判定的输入对得上**。复活闸感知不到仓库变化，故这类照旧每次重判 |

### 第 2 轮：5 条（前 4 条经三路独立核实确认已消除，未换皮重现）

| # | 置信 | 问题 | 修法 |
| --- | --- | --- | --- |
| G1 | 88 | 失效信号漏了「**判定规则本身变了**」这一路输入：人工轮放宽 1.2 判据后，老缓存按旧规则永久卡住 | 1.3 加一条机械兑现：**改动 1.2 判据的人工轮，收尾时清空全仓 `auto:skip`** |
| G2 | 85 | 读侧 fail-closed **没有汇报出口**：云端若取不到时间戳，会一条标都打不上，而 PR 里「本次没有可缓存的」与「机制整体失效」长得一模一样 | 契约表那行的触发条件扩到「**因任何原因**没打上」，并要求**一条都没打成时在 PR 里显式报一句** |
| G3 | 85 | 复核工具是全表调用，天然诱导「调一次 list 再循环打标」，把窗口拉回整批长度（角度 ① 给 ~60 分未报，与角度 ⑤ 分歧，如实并陈） | 采纳批量形态但钉死时序：复核**紧邻**打标循环之前做一次、一口气打完，窗口 = 循环本身（不读正文、秒级）；条数多到循环拖长就拆小批、每批前重新复核 |
| G4 | 82 | 只处理了「明确失败」，没处理「超时 / 结果不确定」—— 按失败记会造成人机状态背离 | 补：结果不确定时**重打一次**（GitHub 侧幂等 no-op），仍不确定记「打标结果未知」 |
| G5 | 80 | `--only` 那行还写着「只跑 1.0 + 1.1 + 1.2」，新增 1.3 后没回来更新 | 明确 `--only` **包含 1.3**，并指出要零写副作用就叠 `--dry-run`（两个开关正交） |

**一条误判已排除**：角度 ② 报「helper 缺 `--no-body` / `issue-label-add` / `updatedAt`」，实为它读了**主仓库 checkout**（仍在 `master`）而非本 worktree 的同名文件；本 worktree 内这三样在 `0eb7f83` / `f557dd6` 就已提交，`--self-test` 通过。

**结论：达 2 轮上限，9 条全修、第 3 轮未跑，留痕放行。**
