# routine-dev 分诊缓存：被判「不自动做」的 issue 打 auto:skip

> 来自 [#122 routine-dev 分诊缓存：被判「不自动做」的 issue 打 auto:skip，下次不再读正文](https://github.com/pkulijing/claude-code-global/issues/122)
> Labels: `type:feat` `area:skill` `priority:P2`

## 背景

`/routine-dev` 每次运行都要把全部 open issue 重新分诊一遍。Step 1.1 的硬过滤（`wontfix` / 在途 PR / `priority:P0` / `area:install`）只看 label，成本可忽略；**真正浪费的是 Step 1.2** —— 它必须读 title + body 才能判定「落点不只在文档上」「需要讨论选型」「正文不足以执行」。

这批被否的 issue 会**长期留在 open 列表里**，于是每周一 / 三 / 五各被完整读一遍、每次得出同一个结论。积压越多，白烧的 token 越多，且只增不减。

## 需求

routine 判定一条 issue 不适合无人值守开发时，把结论**回写成 label 持久化**；下次运行在 Step 1.1（不读正文的那一层）就把它过滤掉。

### 硬约束

1. **不能「误判一次即永久出局」** —— issue 正文后来被补清楚了，必须能自动重新参与分诊。用户已拍板选定**按更新时间自动复活**：issue 被打标之后再被编辑 / 评论过，就重新走完整分诊。
2. **`auto:take` 永远压过 skip** —— owner 背书是最终裁决。
3. **语义不得与 `wontfix` 混淆**：`wontfix` 是人的决策归档、issue 已关闭；本 label 只表示「不适合自动做」，issue 仍 open、人照常可以做。label description 必须写清这一点。
4. `--dry-run` 下**不打任何 label** —— 现有承诺是「跑一次不改变任何外部状态」。

### issue 中列出的候选方向（本轮已实证收敛，见 PLAN.md）

- 方向 A：时间戳存在机器评论里；
- 方向 B：读 timeline 的 `labeled` 事件时间；
- 方向 C：只打标、不做复活（与硬约束 1 冲突，仅兜底）。

### 范围与已知风险（来自 issue 正文）

- **云端能力未实测**：写 label、读 timeline / 评论在 GitHub MCP 里是否可用需确认；本机 `gh` 侧无疑问。两端能力不一致时以「云端能跑」为准 —— 云端是 routine 的主运行形态。
- **本 issue 自己走不了 routine 自动通道**：改动要碰 `.github/labels.yml`，而 `.github/**` 是 routine 的四条红线之一，`auto:take` 也不放宽。本轮必须人工做。
- **打标范围要收紧**：只对 Step 1.2 模型分诊判掉的打；1.1 硬过滤本就零成本，打了纯属噪音。
- **观感风险**：issue 列表上出现一片 skip 标记，容易被读成「这条不会做了」。
- 是否让 `/triage` 感知此 label，待定。

## 交付形态

`skills/routine-dev/SKILL.md` 的分诊步骤 + `.github/labels.yml` 的 label 定义为主，label 命名 `auto:skip`（与 `auto:take` 对称）。具体落点清单以 PLAN.md 为准。
