# 需求：给 `/routine-dev` 减重

## 背景

上一轮讨论中，人类对 claude.ai Routines 这套云端机制下了一个结论性判断：

> 云端没有办法用 UV，没有办法用自定义镜像，没有办法指定 Python 版本，这是 routine 机制的失败。本质上，我长期就不应该依赖这玩意儿做复杂的事情。

这个判断已沉淀为长期约束（memory `cloud_routine_complexity_ceiling`）：**不再往云端 routine 上加复杂度；定时自动化优先本机无头 agent；云端 routine 只留「已明确、不需要执行任何东西」的活。**

`/routine-dev` 是这条约束下最该被审视的对象 —— 它的 `SKILL.md` 已达 **38,292 字节（约 19.4k 字符）**，是整个指令面最大的单文件，比宪法 `GLOBAL_AGENTS.md`（约 11.1k 字符）还大一截。

### 复杂度构成（本轮开工前实测）

按 `## / ###` 分节统计字节：

| 类别 | 占用 | 说明 |
| --- | --- | --- |
| 安全边界（四条红线 / 不触发合入 / 不发评论 / 落点白名单） | ~3.5 KB | **不动**。全是短禁令，本来就便宜 |
| 多 issue / 多 PR 的编排 | ~11 KB | 合批不变式 2.8K + 落点并集复核 2.4K + 在途 PR 照料 2.8K + 其余 |
| `auto:skip` 缓存层 | 5.1 KB + 一个 workflow | 快照 / 时间戳复核 / fail-closed / 残余窗口 / 「改判据要清全仓标」 |
| 双端分岔（本机 vs 云端）+ 无人值守契约 | ~4 KB | 云端弱造成的，只能压不能删 |
| 其余（为什么存在 / PR 模板 / 注册说明） | ~14 KB | 可压但不结构性 |

**结论：占大头的不是安全边界，而是「一次跑多条、出多个 PR、还要管在途 PR」的衍生债，以及一层为省 token 而引入的缓存。**

## 本轮要做的三刀

### 刀 A · 删掉整套 `auto:skip`

删 `SKILL.md` §1.3（5.1 KB）、`.github/workflows/auto-skip-reset.yml`（3.1 KB）、`.github/labels.yml` 里的 `auto:skip` 条目、`references/security-boundary.md` 的「辨析：给 issue 打 `auto:skip`」一节、`README.md` 相应段落、`/triage` 的「自动化」列中 skip 语义。

**理由**：它换来的只是「每周三次少读几条 issue 正文」的 token，代价却是全文最绕的一节 —— 为了防「人在运行途中编辑正文」那个窗口，引入了快照 + 复核 + fail-closed + 「打标循环要够短」+ 「改判据的人工轮记得清全仓标」这一串跨机制耦合，外加一个事件驱动 workflow。**这一刀不改变 routine 做什么，只改变它花多少 token。**

远端已有的 `auto:skip` label 与已打标的 issue 需一并清理（label 删除 = GitHub 自动从所有 issue 摘掉）。

### 刀 B · 删掉 Step 0.5「先照料在途 PR」

删 `SKILL.md` Step 0.5（2.8 KB），连带 `references/security-boundary.md` §3 / §4 / §5（那三节全部是为它写的）。

**理由**：冲突了就让 `ff-merge` 失败、人在手机上看到、回本机让 CC 解 —— 本机 uv / gh / agents 全都在，正是该在有能力的地方做的事。副产品是 **routine 从此不 force-push 任何东西**，攻击面实打实缩一圈。

### 刀 C · 退回「一次运行只做一条 issue、只出一个 PR」

删 `SKILL.md` Step 2 合批整节（2.8 KB）、args 的 `--max-prs`；把「开 PR 前用真实 diff 复核落点」（2.4 KB）塌缩为一条前置检查：**本次落点与任何 open PR 相交 → 放弃本次运行**。Step 3 / Step 4 / 无人值守分岔契约里所有「批」的措辞回退到「本次」。

**理由**：合批的硬不变式、五条聚类规则、共享登记文件分析、落点并集复核、cherry-pick 到已开 PR —— 全部是「一次出多个 PR」的衍生物。代价是每周产出上限降到 3 条（每周一 / 三 / 五各一条）。

## 明确不做

- **不碰安全边界**：四条红线（自己 / `agents/` / `install.sh` / `.github/`）、绝不触发合入、绝不发评论、落点白名单 —— 一个字都不改。
- **不砍自动通道**（原分析里的「刀 D」）：那是产品决策不是简化，本轮不做，留作后续 issue。**本轮三刀都不改变「哪些 issue 会被做」，只改变「一次运行做多少、怎么收尾」。**
- **不动 `/routine-slim`**：它自己的撞车防线（排除所有 open PR 碰过的文件）继续有效，本轮不改。
- **不做压缩式改写**：本轮只做「整块删除 + 措辞回退」，不做 `/routine-slim` 那种「三板斧压缩」。删掉的东西要么真的不再需要，要么已有别处承载。

## 验收

1. `skills/routine-dev/SKILL.md` 从 38.3 KB 降到 **24 KB 上下**（−35% 量级）；`references/security-boundary.md` 相应缩减。
2. `.github/workflows/auto-skip-reset.yml` 删除；`labels.yml` 无 `auto:skip`；远端该 label 已删。
3. **无失效引用**：`scripts/context_budget.py check-refs` 零失败（README / 本仓 CLAUDE.md / `/triage` / `security-boundary.md` 里指向被删内容的引用全部处理干净）。
4. 保留的安全边界文字**逐条对照过**，确认三刀没有顺手削弱任何一条。
