# PROMPT：/review-loop 修两处实战缺口

本轮修 `/review-loop`（round 45 落地）在**真实项目首次实战**中暴露的两个缺口。两者均落在 `skills/review-loop/SKILL.md`、且都是 skill 首次实战的反馈，合并一轮修。

## 缺口 1（本轮主线）：调用方式被 `disable-model-invocation` 堵死

用户在别的项目实际使用 `/review-loop` 时，**第一步就崩了**。

根因：round 45 的 Step 4 调的 `/codex:adversarial-review`（及 `/codex:review`）是 codex plugin 提供的 **slash command**，其 frontmatter 写死 `disable-model-invocation: true`——**只能人手敲斜杠命令，Agent 无法用 Skill / SlashCommand 工具自动调起**。而 `/review-loop` 的全部价值就是「commit 前**自动**触发」，被这个约束彻底堵死。

用户判断：review 代码是通用技能，没必要依赖 codex 官方那个带版本号路径、会随 plugin 升级漂移的 JS 脚本（`codex-companion.mjs`）。应该看清它到底做了什么、有没有值得借鉴的，然后自己在本地写 skill、直接调 codex 命令行。

探明（已实跑验证）：

- codex CLI 有**原生子命令** `codex exec review`，非交互（`approval: never` + `sandbox: read-only`）、输出到 stdout、codex agent 自主翻仓库读上下文，还自动读到双轨软链的 `~/.codex/rules/*.md` 并按项目约定 review。
- 官方那 1027 行 companion 脚本 90% 是为「结构化 JSON 输出 + job 编排 + 状态轮询」服务的基础设施，对「CC 同步拿结果、读自然语言 review」全是负担。唯一值得借鉴的是 `prompts/adversarial-review.md` 里的 `<attack_surface>` 对抗清单。
- 硬约束：`codex exec review --uncommitted`（flag 限定整树未提交）与自定义 `[PROMPT]`（注入 focus）**互斥**。

决策（用户拍板）：摆脱官方 JS 脚本，直接调 `codex exec review`；**PROMPT 主导**（放弃 `--uncommitted` flag），让 codex agent 自己判断「审当前工作树未提交改动」，从而保住「已定前提清单」注入机制、并顺带注入官方攻击面清单。

## 缺口 2（issue #51）：自动修复阶段没内建 TDD

> 来自 [#51 review-loop 自动修复阶段应坚持 TDD（先写红测试→改实现→绿）](https://github.com/pkulijing/claude-code-global/issues/51)
> Labels: `type:feat` `area:skill` `priority:P2`

来源：**devops-bot** round 5「引入自然语言 Agent 能力」的 `/finish` 反思。

问题：`/review-loop` 的 Step 6 把自动修复描述成「列问题 → **修** → 复审」，动词是「修」、**没有内建「先写红测试」的步骤**，诱导 Agent 直接改实现、事后补测试——正是全局宪法 TDD 章明令禁止的「先画靶子后射箭」。

真实事故：codex 报了 4 个正确性 bug，Agent 一口气改了 5 处实现才回头补测试；且补写的并发测试**在旧实现下根本不红**（单线程复现不了 dict-changed-size 那条）＝**假绿**，证明不了它抓得住 bug。改成正序 TDD（先写确定性红测试→看它红→改实现→变绿）后才真正锁死。

这是通用门禁 skill 的流程缺口，非某项目特有——「修」这个动词天然让人跳过「先写红测试」。

落点：把 Step 6「有正确性问题 → 未收敛」的「自动修复」子步**按问题性质分流**：有清晰输入输出契约的代码类问题走 TDD 正序三步 + 假绿硬提醒；纯风格/机械/无法测试复现（含改的就是指令文档本身）按现有节奏。

## 要达到的结果

`/review-loop` 的独立 review 主路径改为「CC 用 Bash 直接调 `codex exec review "<PROMPT>"`」（三段式 PROMPT：范围自述 + 攻击面清单 + 已定前提清单），彻底绕开 `disable-model-invocation` 死路、不再依赖任何 plugin 内部脚本 / 版本化路径；同时 Step 6 自动修复内建 TDD 正序，堵住「假绿」缺口。round 45 的核心机制（自动收口环、每 3 轮人工闸口、审≠写独立性判定、整树 review + gitignore 保护）全部保留。
