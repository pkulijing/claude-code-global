# 用户可配置项机制 —— 设计文档

> 对应 issue [#10](https://github.com/pkulijing/claude-code-global/issues/10)（Spike）。本文档是本轮 Spike 的核心交付，沉淀「机制设计 + 首例落地结论 + 候选项盘点」，供后续 feat 参考。

## 一句话结论

引入一层**扁平 `KEY=value` 用户配置**：仓库内只放示例基线 `user.config.example.env`（committed），用户真实配置 seed 到**仓库外**的 `~/.claude-code-global/config.env`；`install.sh` 以 **user-wins（缺省才填、绝不覆盖）** 语义 seed，并据此应用偏好。首例「git init 默认分支」已端到端落地。

## 背景与问题

仓库此前把所有偏好硬编码在 `GLOBAL_AGENTS.md` / `install.sh` / 各 `skills/`，无「用户可配置」层。直接触发点：`git init` 默认分支有人要 `master`、有人要 `main`，这是个人偏好，不该硬编码进面向所有用户的全局配置。

## 三个验证目标的回答

### 1. 配置放哪？

- **载体格式**：扁平 `KEY=value` env 文件。理由——它是 lowest-common-denominator：shell 能直接解析（无需 jq）、LLM（skill）能直接读、CC 与 Codex 两端共享同一份，且与宪法既有的 `.env.local` / `.env.example` 约定一致。
- **仓库内基线**：`user.config.example.env`（committed），扮演 `.env.example`：只含默认值与注释，可安全提交。
- **用户真实配置**：`~/.claude-code-global/config.env`。
  - 放在**两个 agent home（`~/.claude`、`~/.codex`）之外**的中立目录：它是用户全局偏好，不属于任一 agent 的原生配置，CC/Codex 共用单一真源，避免分叉。
  - 允许 `CCG_USER_CONFIG` 环境变量覆盖路径（测试沙箱 / 高级用户自定义）。
- **不采用** install.sh 交互式询问：`auto-update.sh` 在后台 / 调度器里**非交互**跑 `install.sh`，交互式 prompt 会卡住无人值守同步。配置文件天然非交互、可被多设备同步流程安全反复执行。

### 2. 配置如何被各消费方读取？

统一通过可 source 的库 `scripts/user-config.sh`（双轨软链到两端 `scripts/`）：

| 消费方             | 读取方式                                                                                     |
| ------------------ | -------------------------------------------------------------------------------------------- |
| `install.sh`       | `source scripts/user-config.sh` → 调 `ccg_seed_user_config` / `ccg_apply_git_default_branch` |
| 未来 hook（shell） | 同上 source 后调 `ccg_read_config <KEY>`                                                     |
| 未来 skill（LLM）  | skill 指令里让 agent 直接读 `~/.claude-code-global/config.env` 对应 key（如 commit 署名）    |

`ccg_read_config` 走**安全解析**（grep 行首 `KEY=` + 剥行内注释/引号），**不 blind `source`** 用户文件，避免任意代码执行。

### 3. 多设备自动同步时如何不被覆盖？

`auto-update.sh` 做 `git pull master` + 跑 `install.sh`。关键事实（查实自 `auto-update.sh` / `install.sh`）：

- **进仓库的文件**会被 `git pull` 覆盖；**仓库外的文件**不会。→ 真实配置落在 `~/.claude-code-global/`（仓库外）即天然免疫 pull。
- `install.sh` 的 seed 是 **user-wins**：文件已存在则绝不覆盖，只对 example 新增的 key「逐 key 补缺追加」默认值。→ `auto-update` 反复跑 `install.sh` **安全幂等**，用户改过的值永远保留，新配置项又能随同步下发给老用户。

这与宪法 `.env.local`（真实、gitignore）/ `.env.example`（committed 占位）的拆分**完全同构**。

## 关键设计结论：为何不能复用现有 merge 机制

`install.sh` 已有 `merge_settings`（JSON/jq）与 `merge_toml`（marker 块）两套合并器，但**语义相反、不可复用**：

- 它们是「标量**仓库**胜出」（repo wins）——适合 repo 管控的 hook 集合（仓库要能改写/删除 managed 条目）。
- 用户偏好需要「**用户**值优先」（user wins）——仓库只在用户**未设**时提供默认。

因此本机制是一段**新逻辑**（`ccg_seed_user_config` 的「缺省才填、补缺追加」），而非套用 `merge_settings`。这是本 Spike 最重要的设计判断。

## 首例落地：git init 默认分支

PoC 路径（issue 指定）：配置项 → `install.sh` 读取 → `git config --global init.defaultBranch <值>`。

- 配置键：`GIT_INIT_DEFAULT_BRANCH`，默认 `master`（遵从 issue 偏好）。
- **配置的是 git 本身**：之后任何 `git init`（用户手动或未来 bootstrap skill）都遵守，无需改任何 skill。当前仓库无任何 skill 调 `git init`，故这是干净绿地。
- **opt-out**：值置空 = 不改动用户 git 全局配置。
- **幂等**：重复 install 只是重新断言同一值。

落地文件：`scripts/user-config.sh`（库）、`user.config.example.env`（基线）、`install.sh`（集成）、`docs/27-用户可配置项机制/verify-user-config.sh`（回归测试，T1–T5 全绿）。

## 硬编码偏好盘点（候选清单）

| 候选                   | 现状                                                                                                    | 是否提取        | 备注                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------- | --------------- | ---------------------------------------------------------------------- |
| git init 默认分支      | 无 skill 调用（绿地）                                                                                   | ✅ 本轮首例落地 | `GIT_INIT_DEFAULT_BRANCH`                                              |
| commit trailer 署名    | `skills/commit/SKILL.md:36` 写 `Claude`，`GLOBAL_AGENTS.md:80` 例子写 `Claude Sonnet` —— **两处不一致** | ⏭️ 后续 feat    | 提取为配置 + 顺手修不一致；消费方是 LLM（commit skill 读配置渲染署名） |
| 基础对话语言           | `GLOBAL_AGENTS.md` 硬编码「简体中文」                                                                   | ⏭️ 视需要       | 多为团队统一项，个人可配置价值中等                                     |
| pypi 镜像 / torch 版本 | `GLOBAL_AGENTS.md` Python 规则硬编码                                                                    | ⏭️ 视需要       | 偏团队约定，可配置价值较低                                             |

## 局限性

- 扁平 env 不支持嵌套/数组；若未来出现结构化偏好需求，再评估升级（但当前所有候选都是标量，够用）。
- `ccg_apply_git_default_branch` 在每次 `install.sh`（含 auto-update）都会重新断言 `init.defaultBranch`；若用户绕过本机制、用 `git config` 手改了该键，会在下次同步被改回配置文件的值。规避方式：把值写进 `~/.claude-code-global/config.env`（单一真源），或置空 opt-out。
- 「真实 install 冒烟」需在 merge 回 master 后从**主仓库**跑（从 worktree 跑会把全局软链指向临时 worktree）；本轮以 `bash -n` + 沙箱隔离冒烟覆盖。

## 后续 TODO（派生 feat）

1. **commit trailer 署名可配置**（并修 `commit` skill 与 `GLOBAL_AGENTS.md` 署名不一致）—— LLM 消费方的首个样例。
2. 视需要提取基础对话语言等其余偏好。
3. 若 skill 消费方增多，约定一个统一的「skill 读用户配置」的措辞片段，避免每个 skill 重复描述读取逻辑。
