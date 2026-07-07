# REVIEW 留痕：round 46

本轮改的是指令规则文档（`/review-loop` skill、宪法、README、`/commit` skill），**绝不跳过 review**。本轮 diff 全由 CC 编写、codex CLI 可用 → 用**新的** `codex exec review`（本轮刚落地的调用方式）对本轮 diff 跑独立 review，既是门禁、又是新命令的实战自举。

## 端到端实跑验证（Step 4 新命令，造真实缺陷探针）

在收尾 review 之前，先造含真实缺陷的探针（`_ccg_probe_verify.py`：并发 check-then-act 竞态 + 批量除零 + 一个「已定前提声明不必防御」的 drain），按 Step 4 三段式 PROMPT 实跑 `codex exec review`，验证全链路。**5 项全过**：

| 验证项             | 结果                                                                                                                                               |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| ① 非交互跑通       | ✅ `approval: never` + `sandbox: read-only`，exit 0，无批准交互                                                                                    |
| ② codex 读到改动   | ✅ 自主跑 `git status` / `nl` 读探针全文                                                                                                           |
| ③ 攻击面清单生效   | ✅ 精准命中并发竞态（line 7-8）+ 批量除零 ZeroDivisionError（line 13）                                                                             |
| ④ **已定前提生效** | ✅ **决定性证据**：codex 明说「已按前提忽略 `drain()` 的空列表防御问题」——本会报 pop 空列表崩溃，但因已定前提声明「调用方保证非空」而主动不报      |
| ⑤ 噪音可滤除       | ✅ stdout 混入 `xcrun_db` 报错（每次 git 调用都刷）、`models_manager timeout`、exec trace + 整份 rules 文档；真正结论在末尾 `codex` 段，清晰可分离 |

**实跑新发现的噪音源**（已补进 skill Step 4 噪音清单）：codex 常主动 `cat ~/.codex/rules/*.md`，把整份 rules 文档（数百行）打进 exec trace——量大，别当 review 内容。

## 收尾自举 review（对本轮 diff）

### 第 1 轮：codex 报 2 个 P1（都是真问题，CC 自审极可能漏掉——独立 review 的价值实证）

- **[P1] shell prompt 注入**（Step 4）：原命令把三段式 PROMPT 当双引号位置参数拼进 `codex exec review "<PROMPT>"`。而「已定前提清单」段可能含来自 issue / 用户文本的内容，其中 `"` / 反引号 / `$(...)` 会先被 shell 解析——轻则 prompt 截断、**重则本机命令注入**。讽刺：round 45 我曾为 `/codex:adversarial-review` 加 `--` 隔离防注入，换调用方式后又把这层防护弄丢了。
  - **修复**（走「改的是指令文档」档、无红测试可写）：命令改为 `codex exec review ... - <<'CODEX_REVIEW_PROMPT'` **从 stdin 传 PROMPT** + **带引号 heredoc delimiter**（体内不做 shell 展开）。**已实测**：`$(whoami)`、反引号原样落入 prompt、未被执行。
- **[P1] 把 gitignore / read-only 当读取隔离**（安全段）：原文称「敏感内容靠 gitignore 保护 + read-only sandbox，review 天然不碰」。但 codex 是能自主跑 shell 的 agent——`read-only` 只挡写、`.gitignore` 只挡 git 发现，**都挡不住 `cat .env.local`**（实测它会主动 cat rules 文档）。这是虚假安全感。
  - **修复**：① PROMPT 第 1 段明确**禁止 codex 读取 `.env*` / gitignored / 密钥文件**；② 安全段重写为诚实的「两层软防护 + 边界声明」（指令约束是软防护、非硬隔离；绝密内容不应在装 codex 的机器上跑本 skill）；③ 同步「明确不做」段措辞。

### 第 2 轮：复审（用第 1 轮改的 stdin heredoc 形态重跑）—— 又抓出 1 个 P1

- **[P1] 固定 heredoc delimiter 仍可被提前闭合**（Step 4）：第 1 轮改的 `<<'CODEX_REVIEW_PROMPT'` 用**固定** delimiter。单引号 delimiter 只挡变量/命令展开，**挡不住 PROMPT 正文里恰好有一行等于 `CODEX_REVIEW_PROMPT`**——来自 issue/用户文本的已定前提若含这一行，就能**提前闭合 heredoc**、让后续内容重新被 shell 当命令解析。原 skill 那句「任何字符都原样进入」是过度承诺、会误导执行者。**这是我第 1 轮的修复自己引入的残余漏洞**——活教材：修复本身会引入新问题，故「修完必须复审」不是形式。
  - **修复**（第 2 轮）：**彻底弃用 heredoc**，改为 **CC 用 Write 工具把 PROMPT 写进 scratchpad 临时文件，再 `codex exec review - < 文件`**。PROMPT 只作为**文件内容**存在、与 shell 解析完全无关，不再有 delimiter 概念、零注入面。**已实测**：正文塞 `$(whoami)`、反引号、甚至一整行 `$(rm -rf ...)`，全部原样进 prompt、`rm` 未执行。

### 第 3 轮：复审（用第 2 轮改的临时文件 stdin 方案自举重跑）—— 抵 3 轮人工闸口

codex 确认「临时文件 stdin 方案本身消除了命令行/heredoc 注入面」（注入面彻底关闭），但又报：

- **[P1] 「密钥不落工作树明文」与宪法冲突**（安全段）：我第 1 轮补的安全段写「真正的密钥本就不落工作树明文」，但宪法「环境变量管理」明确要求 `.env.local` **存真实值、放项目根、仅 gitignore**——它**就是**工作树明文文件，read-only codex 照样读得到。这句话会让人误以为按宪法放的 `.env.local` 安全，反而削弱刚补的软防护声明。**这是真硬伤**（自相矛盾）。
  - **修复**：删掉该臆想的"纵深"层，改为诚实表述——敏感防护**只有一层软防护**（PROMPT 指令禁读，依赖模型遵守）；**唯一硬保证是「绝密内容别出现在这台机器上」**。
- **[P2] 临时 prompt 文件位置**：Step 4 只说写到 scratchpad、没约束在 worktree 外，否则会被当 untracked 一并审、污染 `/commit`。
  - **修复**（顺手轻量补严）：Step 4 明确「临时文件必须在被审 worktree 之外（用会话 scratchpad）+ review 后删除」。

**→ 抵达「每 3 轮强制人工闸口」硬规则**：停下交回用户。用户裁定：**修 P1 那条（已修）、P2 顺手补严（已修）、就此收敛不再 review**。

## 关键反思：codex review 的信任边界（用户一手判断）

用户在 3 轮闸口处的原话：**「加入后开发效率降低太多了，codex review 总在纠缠一些细枝末节的 corner case，它似乎不值得这么高的信任。」**

这是本轮最有价值的一手数据，如实记录：

- **前 2 轮（4 个 P1）确有价值**：shell 注入、heredoc delimiter 可闭合——都是 CC 自审极可能漏掉的**真安全漏洞**，独立 review 的核心价值在此兑现。
- **但第 3 轮起明显边际递减**：codex 每轮总能再挖一个更细的 corner case（密钥表述精确性、临时文件位置），从「真漏洞」滑向「表述打磨」，**问题空间近乎无穷**（正是 SKILL「为什么是硬闸」段所述）。若无 3 轮闸口，会一直被拽着走、效率大跌。
- **暴露的真问题**：当前 review-loop 把 codex 的**每一条**都当「需响应项」，未区分「真会出错」与「理论上更严谨」。codex 不该被给这么高、这么无差别的信任——**它是有价值的第二双眼睛，不是必须逐条满足的权威**。
- **后续方向**（转 SUMMARY「局限性 / 后续 TODO」）：review-loop 的运作方式需重新设计——如何用低摩擦方式获得独立 review 的**抓真漏洞**价值，同时不被 corner-case 洁癖拖垮效率。3 轮闸口是**止损**，不是**解决**；解决要靠更好地校准「哪些值得修」。用户将另行思考。
