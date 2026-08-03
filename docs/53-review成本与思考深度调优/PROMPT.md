# PROMPT · review 成本与思考深度调优

> 来自 [#98 review-loop：reviewer 子 agent 继承主会话 xhigh 思考档，成本高且助长钻牛角尖](https://github.com/pkulijing/claude-code-global/issues/98)
> Labels: `type:perf` `area:skill` `priority:P0`

## 背景

`/review-loop` 是提交前的自动门禁，每次 `/commit` 都会跑。它委派出去的 reviewer 子 agent **继承主会话的 reasoning effort**——主会话在 `xhigh` 时，orchestrator + 3～5 个 reviewer 全部以 `xhigh` 跑。

这带来两个当下最痛的问题（人类原话）：

- **成本**：5 小时额度动不动被 review 吃掉 50%。
- **效率**：一次 review 动辄卡住半小时。

而收益并不对称。issue 里的实证（devops-bot round20，2026-08-02～03，一轮开发跑了 6 次 review）：

- 单轮重档耗时 10–25 分钟、子 agent token 13–23 万（C3 那轮 24 分钟 / 22.6 万 token）；
- 真正阻断的高置信 finding 全轮只有 7 条，且**都来自「多角度独立 + 探针验证」而非单个 reviewer 想得深**——典型如 C3 的「agent 路径丢弃已验证身份、用猜出的邮箱决定凭证收件人」，是**契约追踪**发现的，不是深度推理发现的；
- 同期被置信闸门（`<80 丢弃`）滤掉的低置信项约 20 条（30–72 分），包括「`_flatten` 嵌套两层的假想 payload」「锁 key 未做大小写归一」这类明显的钻牛角尖产物。

**等于花深思考的钱，去生产注定被扔掉的东西。**

## 需求

限制 review 的思考深度，把成本与延迟压下来，同时不牺牲真正驱动检出率的东西。要求：

1. **先做网络调研**，回答两个问题并把结论写进 `PLAN.md`：
   - generally，vibe coding 场景下代码该怎么 review？
   - 基于 Opus 5 开发的代码该怎么 review？
2. 结合调研结论**决定怎么做**，而不是照搬 issue 里的建议方案。
3. 落地为可复用的机制，而非一次性调参。

## issue 已给出的方向（供参考，非定论）

**优先：给 review 建专用 agent 定义。** `.claude/agents/*.md` 的 frontmatter 可以钉死该类型的 model **与 reasoning effort**。据此：

1. 在 `claude-code-global` 新增 agent 定义（如 `agents/reviewer.md`），`model: sonnet` + effort 降档（深审角度可单独留一个用 opus）；
2. `install.sh` 把它软链到 `~/.claude/agents/`（当前该目录不存在，属从零加）；
3. `/review-loop` 的委派从 `subagent_type: "general-purpose"` 改成这些专用类型。

这样 reviewer 固定低档跑，主会话仍可保持 `xhigh`，两者解耦。

**备选：Workflow 工具**的 `agent()` 支持逐个 `effort`，但它需要用户显式 opt-in、比改 skill 重，不适合作为 commit 前自动环的默认路径。

## 约束与不变量

改动落在 `/review-loop` 这条**门禁自身**上，以下三条骨架来自宪法，属**已定前提，本轮不推翻**：

- **收敛靠「运行验证 + 高置信过滤」**，不是靠 reviewer 挑不出为止；
- **review 永远在独立 context 的子 agent 里跑**（唯一例外是既有降级链）；
- **2 轮不收敛自动留痕放行**，不停下问人。

同时：

- 本仓 `CLAUDE.md` 明写 `skills/*.md` 属指令规则文件，**改它自己必须走 review**，不能因为「只是改文档」跳过；
- `/review-loop` 的 SKILL.md 是 review 机制的**单一真源**，宪法与 `/commit` 只留触发点，改动不得把细节外溢回宪法；
- 该 SKILL.md 被 CC 与 Codex **双端共读**，Codex 端没有 Agent 工具、也没有 `~/.codex/agents/` 这个概念，新机制不能让 Codex 端的降级链失效。

## 待确认项（issue 原文列出，需在 PLAN 中给出处理方式）

- reviewer 降档后，重档场景（并发 / 状态机 / 难复现）的检出率是否明显下降——issue 建议挑一个已知有真 bug 的历史 diff 做 A/B（round20 的 C2 give-up 锚点 bug、C3 身份误投是现成样本）。
  **已知障碍**：`devops-bot` 仓库在本机 `$HOME` 下四层内找不到，round20 的原始 diff 当前不可直接取用。
- `effort` frontmatter 的确切键名与可选值需按当前 CC 版本核实后再写进定义文件。

## 交付物

- `docs/53-review成本与思考深度调优/`：`PROMPT.md`、`PLAN.md`、`SUMMARY.md`、`REVIEW.md`
- 机制落地：agent 定义 + `install.sh` 部署 + `/review-loop` skill 改写
- 调研结论（带出处）沉淀进 `PLAN.md`，作为档位选择的依据而非事后解释
