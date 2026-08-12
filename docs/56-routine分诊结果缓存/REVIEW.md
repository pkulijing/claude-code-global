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
