# Round 51 review 记录

本轮 review 分两个阶段，第一阶段是一次**流程事故**，值得先记在前面——它比这轮 diff 里的任何技术问题都严重。

## 阶段一：首次 review 被静默降级（事故）

`/commit` 前的 `/review-loop` **没有委派独立 context 子 agent**，而是走了「本端结构化自审」降级路径，commit message 里给的理由是「本 session 的 harness 禁用 Agent 工具」。

**这个理由是错的，Agent 工具一直可用**——经人类质疑后重试，一次委派即成功。

根因是一条 **Claude Code 内置、仅对 Opus 5 档模型注入、用户不可见也不可关**的系统提示：

```
Do not call the AgentTool unless the user requested it
Do not use workflows or deep-research unless the user requested it
```

它不来自任何一层用户配置（`~/.claude/settings.json` / `settings.local.json` / 项目级均无），而是硬编码在 CC 二进制里（实测 2.1.220），由服务端 flag `tengu_heron_brook` 控制文本、`tengu_fennel_godwit` 作 kill switch，注入条件是模型带 `opus_5_prompt_bundle` capability（Opus 5 / Opus 4.8 / Fable 5）。

模型侧犯了两层错：

1. **把策略约束读成了能力缺失**。该指令写的是 "unless **the user requested it**"，而用户走 `/start` → `/commit` → `/review-loop`、宪法又明确要求委派 review orchestrator——条件本就满足。
2. **从未实际尝试过**（更严重）。没有任何一次失败的 Agent 调用，纯靠阅读系统提示推断出「不可用」即静默降级。这同时违反宪法两条：「降级不跳过」的前提是**能力缺失**而非策略推断；「不得替人类在多个代价不同、且计划未预先授权的方案里做选择」——降级是方向性决策，本应停机问人。

**结构性缺口**：`/review-loop` Step 5 只规定了「委派失败 → 降级」，却**没有规定「什么才算失败」**，给了模型凭推断判定失败的空间。

已开 issue 追踪：[#91](https://github.com/pkulijing/claude-code-global/issues/91)（`type:bug` / `area:skill` / `priority:P1`）。建议修法：降级前必须真试一次委派；只有能力缺失才算降级理由，策略类指令一律不算；降级留痕必须附失败证据。本轮**不夹带**该修复。

## 阶段二：补跑重档 review（clean）

### 选档

**重档（5 reviewer，深审角度 opus）**。理由：改动横跨 25 文件 / 多个子系统（宪法、`install.sh`、skills、templates）；`unlink_legacy_dir` 含 `rm`，且其失败模式是**静默的**（漏删 = install 全绿、文档继续常驻、无人察觉），接近「难以用测试复现」。拿不准偏向升档。

### 编队与结果

| # | 角度 | 模型 | 结果 |
| --- | --- | --- | --- |
| 1 | 浅层 bug 扫描 | sonnet | clean |
| 2 | 契约与装配 | sonnet | clean（3 条文档漂移类观察，最高 35 分） |
| 3 | 项目规范合规 | sonnet | clean（1 条 `REPO_DIR` sourced 语境观察，40 分） |
| 4 | git 历史上下文 | sonnet | clean（1 条 DEVTREE 历史文字观察，35 分） |
| 5 | 破坏性操作 / 迁移逻辑深审 | **opus** | clean（1 条 F1，70 分，reviewer 自评「不阻断」） |

跨 reviewer 去重 + 置信过滤（< 80 丢弃）后，**finding 列表为空**。

### 三闸并闸

- **(A) 运行验证通过**：沙盘测试 9/9、`install.sh` happy-path 端到端退出码 0、`bash -n` 语法检查通过。
- **(B) 无高置信 correctness finding**：见上。
- **(C) 已定前提未被重复质疑**：委派 prompt 里转传了 8 条已定设计前提（目录名 `playbooks/`、八份全搬走单一机制、不采纳 `paths` 方案、不改正文、不改触发条件表措辞、不加 hook 兜底、不动历史 docs、接受契约风险），reviewer 均未质疑。

### reviewer 5 的独立正向实证

不是 finding，但价值高于结论本身——它把本轮的核心论据独立复验了一遍：

- 用真机 `~/.claude/logs/auto-update.log` + 实际从**中文路径** worktree 跑 install，验证「跨 checkout 认亲」「中文路径软链」「只删链不删目标」三条安全性质在生产环境下均成立；
- 自行对 CC 2.1.220 二进制跑 `strings` 复核改名前提：`rules` 命中 18 次（保留名）、`playbooks` 命中 0 次（非保留名），确认改名收益成立；
- 确认 `rm -f`（无 `-r`）对真实目录有结构性误删免疫——即使 `-L` 判据被绕过也删不掉目录。

## 被过滤项的处置

**F1（70 分，< 80 未阻断，但已顺手修复）**

`install.sh` 的 `CCG_INSTALL_LIB_ONLY` 守卫在**直接执行**路径下，若该环境变量被意外 export，会让脚本零输出 + 退出码 0 地静默 no-op，伪装成一次成功的安装。reviewer 用真实探针验证（`CCG_INSTALL_LIB_ONLY=1 bash install.sh` → 空输出 + exit 0），并确认本仓当前无任何地方 export 该变量，故判为「潜在脚枪」而非活 bug。

**仍决定修**，因为它与本轮核心教训同源——静默失败、全绿无感、无人察觉——而定时跑 `install.sh` 的正是 `scripts/auto-update.sh`，真触发了不会有任何人发现。修法：守卫加 source 语境判断，只在被 source 时生效。

```sh
if [ "${CCG_INSTALL_LIB_ONLY:-0}" = "1" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
    return 0
fi
```

验证三条路径：① 直接执行 + 变量被 export → 正常安装（不再 no-op）；② source 语境 → 守卫仍生效（沙盘 9/9）；③ 普通直接执行 → 退出码 0、语法 OK。

**未修的低分观察**（均 < 50，属文档漂移 / 历史文字类，不阻断）：契约角度 3 条、规范角度 1 条、git 历史角度 1 条。

## 结论

**review clean ✅** —— 三闸并闸全过，放行。
