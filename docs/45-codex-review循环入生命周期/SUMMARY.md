# SUMMARY：把「codex review 循环」纳入开发生命周期（round 45）

> 关联 issue：[#24](https://github.com/pkulijing/claude-code-global/issues/24)（`type:feat` / `area:skill` / `priority:P1`）

## 开发项背景

**要解决的问题**：同一个模型自审自写的代码，盲区一致、极难发现问题——尤其多线程 / 并发 / 复杂逻辑这类难复现改动。来源 teleop-operator round 12 的硬实证：一处 grpc.aio 消费迁专用线程的重构，CC 自审只发现 2 个并发隐患，换独立模型（codex）review 又补出 3 个 P1（其中「优雅停不可达」CC 完全漏判）。`/code-review`（CC 审自己 diff）解决不了，因为是同一个脑子。

**目标**：把「引入独立第二模型 review」从「偶尔想起来 / 人手动触发」变成**每个 commit 都必经的自动环**，迭代到干净才放行。

## 实现方案

### 关键设计

1. **commit 时机前移 + 内嵌 review**（核心工作流变化）：执行阶段 commit 由 Agent 自主把控——判断一个开发单元完成即主动 `/commit` 收口、不干等用户；每次 commit 前自动经 `/review-loop` 迭代至 clean。人类 review 前移到 `/finish`，面对的是每个 commit 都已过 review 的干净分支。

2. **「独立」的要害是「审的模型 ≠ 写这段 diff 的模型」**（看 diff 的 **author**、不是 **executor**）：CC 写的代码 codex 审才独立；codex 写的代码再用 codex 审就是同模型自审、不算独立。多 Agent 混作（如 Codex 写、CC 提交）时尤其要看「谁写的」。

3. **review 整个工作树、不做文件集隔离**：让独立模型看到全部 diff 并自由翻阅任意未改文件看上下文（一处改动的正确性常依赖它调用/被调用的其它文件）；安全（凭据不外发）**靠 `.gitignore`**，不靠 skill 自己 stash/隔离。

4. **每 3 轮强制人工闸口**（防无限迭代烧 token 的硬规则）：自动修复每满 3 轮必停下交回用户，授权后再来至多 3 轮，永不自动突破。

5. **传「已定前提」给 codex**：用 `/codex:adversarial-review --wait --scope working-tree -- <前提>`（`--` 隔离防注入）把人类已拍板的设计决策喂给 codex，让它在正确前提下 review、不在已否决方向反复打转。

6. **降级极简**：codex 不可用（没装 / 命令失败）时停下告知用户后降级本会话自审并显著标注；采「乐观试跑 + 失败降级」，不悲观预检 token/登录。

### 开发内容概括

- **新增 `skills/review-loop/SKILL.md`**（~115 行）：Step 0（已定前提清单）→ 1（确认变更、整树）→ 2（琐碎跳过，配置/指令文件不跳）→ 3（独立性判定：审≠写 author）→ 4（codex review，`--` 隔离 focus）→ 5（降级自审）→ 6（分诊+修复，3 轮人工闸口 + 修复后重跑测试）。
- **改 `skills/commit/SKILL.md`**：lint 之前内嵌 review-loop（放 lint 前是让 lint 覆盖 review-loop 的自动修复）。
- **改 `GLOBAL_AGENTS.md`**：「核心开发模式」加 commit 自主收口约定；新增「独立模型 review」小节（含 3 轮闸口、独立性=审≠写、配置/指令不跳过）。
- **改 `README.md`**：Skills 表加 `/review-loop` 行、`/commit` 行补 review、工作流串联、引导语。

### 额外产物

- **`docs/45-*/REVIEW.md`**：完整记录本轮「用 review-loop review 自身实现」的约 20 轮自举迭代——每轮 codex 报了什么、怎么修、两次人类关键干预。本身就是 issue #24 论点的活标本。

## 局限性

1. **Codex 端无独立 reviewer**：目前无「从 Codex 会话调起 CC 做 review」的入口，故 Codex 写的代码只能降级本会话自审（带标注）。
2. **独立性判定靠 Agent 自觉判断 diff author**：无机械化的「作者溯源」，混合作者场景靠 Agent 结合上下文判断、拿不准时问用户。
3. **本轮未在真实代码改动上验证**：本轮改的全是文档/skill，review-loop 对「真实代码 diff + 有测试」的完整链路（尤其「修复后重跑测试」）尚未实战跑过。

## 后续 TODO

1. 补齐「Codex 端调起 CC 做独立 review」的入口，让双端都有真正的独立 reviewer。
2. 在一次**真实代码开发**轮里实战 review-loop（验证「修复后重跑测试」链路）。
3. 观察「每 3 轮人工闸口」在真实使用中的体感，看 3 轮是否合适。

## 可沉淀项

本轮自举暴露出的**元经验**极有价值，值得沉淀（部分已写进 skill/宪法本身）：

1. **纯策略/规则类文档的 review 会趋于无限**：这类文档在描述「应该怎么做」，问题空间近乎无穷、reviewer 总能再挖一个更极端的边缘场景。**教训**：这类东西不该追求「codex 报 clean」，而该由人判断「核心稳了就停」——这正是「每 3 轮人工闸口」的由来（已写进 skill/宪法）。

2. **别边写边 review**：本轮前 11 轮是边写 skill 边审半成品，大量轮次浪费在「自己没写好→codex 指出→改→又漏一处同步」的自消耗。**应先写完整、自己通读保证多文档一致，再一次性 review**。（去向：可写进 `/review-loop` 或开发约定。）

3. **独立模型会在错误/不适用前提上锲而不舍地帮你「修」**，越修越复杂——人类质疑「这件事本身该不该做 / 是否过度设计」的价值不可替代。本轮两次人类干预（推翻「文件集隔离」、叫停「降级过度设计」）是收敛的关键转折。

4. **定期开全新 review 线程（不带历史、不带 focus）从零 review**，能戳破「层层补丁把简单问题搞复杂」——中立眼光是一味解药。
