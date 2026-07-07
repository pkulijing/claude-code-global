# SUMMARY：/review-loop 修两处实战缺口 —— 改用原生 codex CLI + 自动修复走 TDD 正序

## 开发项背景

round 45 落地的 `/review-loop`（commit 前自动引入独立模型 review）在**真实项目首次实战**中暴露两个缺口，均落在 `skills/review-loop/SKILL.md`、同源，合并一轮修：

- **缺口 1（主线 bug）**：Step 4 调的 `/codex:adversarial-review`（及 `/codex:review`）是 codex plugin 的 **slash command**，frontmatter 写死 `disable-model-invocation: true`——**只能人手敲、Agent 无法用 Skill / SlashCommand 工具自动调起**。而 `/review-loop` 的全部价值就是「commit 前**自动**触发」，第一步就崩。
- **缺口 2（issue #51，devops-bot round 5 实战反馈）**：Step 6 把自动修复写成「列问题 → **修** → 复审」，动词是「修」、无「先写红测试」步骤，诱导 Agent 直接改实现、事后补测试。真实事故：codex 报 4 个 bug，Agent 一口气改 5 处实现才补测试，且补写的并发测试**在旧实现下根本不红**（＝假绿，证明不了抓得住 bug）。

## 实现方案

### 关键设计

- **改用 codex CLI 原生 `codex exec review`**（缺口 1 核心）：探明官方 1027 行 `codex-companion.mjs` 90% 是为「结构化 JSON + job 编排 + 状态轮询」服务的基础设施、对本场景全是负担，且带版本号路径会随 plugin 升级漂移。`codex exec review` 是干净的原生子命令（非交互、只读、codex agent 自主翻仓库），直接 Bash 调即可。唯一从官方**借鉴**的是 `prompts/adversarial-review.md` 的攻击面清单（auth / 数据损坏 / 回滚 / 竞态 / 空态 / 版本漂移 / 可观测性）。
- **PROMPT 主导，弃 `--uncommitted` flag**：实跑发现 `--uncommitted` 与自定义 `[PROMPT]` **互斥**。为保住 round 45 核心的「已定前提清单」注入，走 PROMPT 主导——不用 git 输出替 codex 划范围，让它自己判断审什么（呼应用户「别拿 git 输出限制 review 范围，让 agent 区分」）。三段式 PROMPT = 范围自述（含禁读敏感文件）+ 攻击面清单 + 已定前提清单。
- **PROMPT 经临时文件 + stdin 传入（防注入，自举 review 逼出来的）**：PROMPT 的已定前提段可能含来自 issue / 用户文本的内容。最初直接当命令行参数（shell 注入）、改 heredoc（固定 delimiter 仍可被正文提前闭合）都不安全；**最终定为 CC 用 Write 工具把 PROMPT 写进仓库外临时文件、再 `codex exec review - < 文件`**——PROMPT 只作为文件内容存在、零 shell 解析面。实测正文塞 `$(rm -rf ...)` 都原样进 prompt、未执行。
- **Step 6 自动修复按问题性质分流走 TDD 正序（缺口 2）**：有清晰 IO 契约的代码类 bug → TDD 正序三步（**先写会红的复现测试 → 确认旧实现上真红 → 改实现变绿 → 回归**）+ **假绿硬提醒**（旧实现上就绿的测试证明不了抓得住 bug）；纯机械修复或改的就是指令 / 文档本身 → 无红测试可写、直接改。与宪法 TDD 章「适用范围 + 例外」一致。
- **顺带卸载 codex plugin**：review-loop 已不依赖 plugin（只用 codex CLI 本体），且 plugin 的 rescue 能力用户不需要，故卸载 plugin + 移除 marketplace，保留 CLI 本体。

### 开发内容概括

改 4 个文件：`skills/review-loop/SKILL.md`（核心，两处缺口 + 3 轮自举 review 修出的 4 P1 都在此）、`GLOBAL_AGENTS.md`（命令引用 + TDD 要点）、`README.md`（命令引用 + 修正「最多 3 轮」为「每 3 轮闸口」）、`skills/commit/SKILL.md`（同步「最多 3 轮」措辞）。无需 `install.sh`（目录已双轨软链）。

### 额外产物

- `REVIEW.md`：完整记录本轮**用新命令自举跑的 3 轮 codex 独立 review**——前 2 轮抓出真注入漏洞（4 P1）、第 3 轮起边际递减，并如实记录用户在 3 轮闸口处对 review-loop 信任边界的一手判断。
- 多次端到端实跑验证（造真实缺陷探针 + 危险字符注入探针），坐实新命令 5 项能力 + stdin 防注入。

## 局限性

- **review-loop 的运作方式本身需重新设计（本轮最重要的发现）**：本轮用新命令自举 review 时，codex **把每一条都当「需响应项」、未区分「真会出错」与「理论上更严谨」**。前 2 轮抓出的 shell 注入 / heredoc 可闭合是**真安全漏洞**、独立 review 价值兑现；但从第 3 轮起总在纠缠细枝末节的 corner case（表述精确性、临时文件位置），**开发效率降低太多**。用户明确判断：**「codex review 不值得这么高、这么无差别的信任——它是有价值的第二双眼睛，不是必须逐条满足的权威。」** 现有的「每 3 轮人工闸口」是**止损**、不是**解决**。
- **敏感文件防护只有一层软防护**：codex 是能自主跑 shell 的 agent，`read-only` 只挡写、`.gitignore` 只挡 git 发现，都挡不住它 `cat .env.local`（宪法要求 `.env.local` 就放工作树明文）。唯一硬保证是「绝密内容别出现在这台机器上」。已在 skill 诚实声明，但这是设计取舍、非完美隔离。
- **Codex 端无独立 reviewer**：本 skill 双端共享，但 Codex 端跑时「独立第二模型 = CC」的入口尚未打通（后续 TODO，非本轮范围）。

## 后续 TODO

1. **重新设计 review-loop 的运作方式（高优先，用户将另行思考）**：核心矛盾是「如何低摩擦地获得独立 review 的**抓真漏洞**价值，同时不被 corner-case 洁癖拖垮效率」。可能方向——① 校准收敛判据，让 codex 只报「真会出错」、显式抑制「理论更严谨」类；② 给 review 结果分级、Agent 有权判「此条不值得修」而非逐条响应；③ 调整触发范围（不是每个 commit 都值得；纯指令 / 文档轮的问题空间近乎无穷，尤其烧）；④ 重新审视 codex 的信任权重。
2. 打通「Codex 写的代码调起 CC 做独立 review」的入口（round 45 已列）。

## 可沉淀项

本轮全程在 claude-code-global 内（自指），跨项目资产候选走本地 `/backlog`，不 API 自 file：

- **review-loop 信任边界问题** → 值得**单独立项重新设计**（对应「后续 TODO 1」）。这是跨项目通用的重要发现：独立模型 review 的价值真实（抓真漏洞），但当前「逐条响应 + 无差别信任」的运作方式摩擦过大。建议 `/backlog` 起 issue，作为 review-loop v2 的设计入口。
- 本轮修的两个缺口本身即是给全局 skill 的沉淀（已随本轮落地），无需另立。
