---
name: triage
description: 盘点当前仓库的 open issue，按 priority × scope 打出一张排序表并给一条下一轮开发建议。只读、无副作用、不写任何本地文件
disable-model-invocation: false
---

盘点当前仓库的 open issue，按 **priority × scope** 打一张表，末尾给**一条**明确推荐 + 理由。

## 为什么存在

「未关闭项速览」原本由 saved query 承担（按 priority label 过滤 open issues），但它**只做过滤、不做判断** —— priority 是唯一维度，scope（多大、有没有前置依赖）完全不体现，要知道一条贵不贵得逐个点进 issue 读正文。

而挑下一轮时的真实决策是 **priority × scope 的二维权衡**：一条 P0 但 XL 的，未必该排在一条 P2 但 S 的前面。这个权衡每轮都要人重做一遍。

**本 skill 不取代 saved query** —— saved query 是随时扫一眼的常驻入口，本 skill 是「**要挑下一轮了**」时跑一次的决策辅助。

## 三条硬约束

1. **只读、无副作用**：不改 issue、不打 label、不写任何本地文件、**不自动 `/start`**。决定权留给人。
2. **跨平台**：一律走 `python3 $HOME/.claude/scripts/platform_issue.py`，**不直调 `gh` / `glab`**（宪法明令，且 GitLab 端与云端 sandbox 都没有 `gh`）。
3. **不新增本地索引**：与「issue 是单一真源」一致，本 skill 不落任何缓存 / 清单文件。

## Step 1 · 拉 open issue

```bash
python3 $HOME/.claude/scripts/platform_issue.py issue-list
```

按 `git remote get-url origin` 自动判定 GitHub / GitLab，stdout 是归一 json 数组（`number` / `title` / `body` / `url` / `labels`，与 `issue-view` 同 schema）。

**拿不到数据就把原因照实说出来并停在这里，不要凭印象手写一张表。** 本子命令实际会出现的退出码只有三种：**2** 平台未知（无 origin / 自托管 URL 不含 `gitlab` 字样）、**4** `gh` / `glab` 没装、**1** 其余一切失败（含 **auth 过期** —— 那是底层 CLI 的非零退出，helper 原样透传它的 stderr，**不会**变成 `scripts/platform_issue.md` 降级表里的 3；exit 3 只有 `auth-status` 子命令才产生）。所以判 auth 问题要看 stderr 内容，别按数值分支。

> **云端 sandbox 跑不了这条**（`gh` / `glab` 均未安装），那边要走 GitHub MCP。本 skill 当前只面向本机；真要上云端时换的是 Step 1 这一步的取数方式，后面的判断逻辑不用动。

## Step 2 · 逐条定档

每条 issue 取三样：

- **priority**：直接读 `labels` 里的 `priority:*`。没有就标 `未标`。
- **area**：读 `labels` 里的 `area:*`。
- **scope**：**优先读 `body` 里现成的 `scope` 字段**（feat / spike 两个 issue 模板本来就有这栏），归一到 `S` / `M` / `L` / `XL`。

**scope 的两条来源必须在表里区分开**：

| 来源 | 标记 | 说明 |
| --- | --- | --- |
| issue 正文的 scope 字段 | `S` / `M` / `L` / `XL` | 确定性高、可追溯 |
| 正文没写、由模型现估 | `S?` / `M?` / `L?` / `XL?` | 同一条 issue 两次跑可能给不同档 |
| 正文没写且估不出 | `未填` | **如实标，不许猜一个填进去** |

**本仓早期 issue 的正文没有 scope 字段**，覆盖率天然不齐 —— 表里出现一片 `未填` 是数据的实况，不是本 skill 没跑好。

## Step 3 · 出表 + 给一条推荐

按 priority 升序（P0 在前）、同 priority 内 scope 小的在前，打一张表：

| # | priority | scope | area | 一句话 |
| --- | --- | --- | --- | --- |
| #98 | P0 | S | skill | …… |
| #39 | P0 | XL | skill | …… |

然后给**一条**推荐，附理由。理由里必须**把依据摊开**：

- priority 来自哪个 label；
- scope 来自正文字段还是模型现估（后者明说）；
- 为什么它排在别的 P0 前面。

> **防权威性错觉**：推荐结论是 LLM 判断，不是计算结果。把依据摊开的目的就是**让人一眼能推翻它** —— 给一个看起来很确定、却没法核对的结论，比不给更坏。

## 明确不做

- **不改任何 issue 状态、不打 label、不发评论。**
- **不自动开轮** —— 人看完表自己决定跑不跑 `/start <issue#>`。
- **不写本地索引 / 缓存文件。**
- **不列 closed issue** —— 本 skill 只回答「下一轮挑什么」。
