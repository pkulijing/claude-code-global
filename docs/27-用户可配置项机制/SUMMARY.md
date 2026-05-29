# 开发总结 · 引入用户可配置项机制（首例：git init 默认分支）

> 对应 issue [#10](https://github.com/pkulijing/claude-code-global/issues/10)（Spike）。完整机制设计见同目录 `DESIGN.md`，实现计划见 `PLAN.md`。

## 开发项背景

仓库此前把所有行为/偏好硬编码在 `GLOBAL_AGENTS.md` / `install.sh` / 各 `skills/`，没有「用户可配置」这一层。直接触发点：`git init` 默认分支有人偏好 `master`、有人偏好 `main`，这是个人偏好，不该硬编码进面向所有用户的全局配置。本轮作为 Spike，验证并引入一层最小可行的用户可配置机制，并把「git init 默认分支」首例端到端落地。

## 实现方案

### 关键设计

- **载体**：扁平 `KEY=value` env 文件。仓库内只放示例基线 `user.config.example.env`（committed），用户真实配置 seed 到**仓库外**的 `~/.claude-code-global/config.env`（CC/Codex 共用单一真源）。这与宪法 `.env.local` / `.env.example` 拆分同构。
- **最重要的判断——不能复用现有 merge**：`install.sh` 的 `merge_settings` 是「标量仓库胜出」（repo wins，适合 repo 管控的 hook），而用户偏好需要「用户值优先」（user wins）。两者语义相反，故新写一段 `ccg_seed_user_config`（缺文件才 seed、已存在绝不覆盖、example 新增 key 才逐 key 补缺追加）。
- **sync 安全**：真实配置在仓库外 → `git pull` 不触碰；seed 是「缺省才填」→ `auto-update.sh` 反复跑 `install.sh` 安全幂等，用户改过的值永远保留，新配置项又能随同步下发。
- **首例**：配置键 `GIT_INIT_DEFAULT_BRANCH`（默认 `master`）→ `install.sh` 读取 → `git config --global init.defaultBranch`。配置的是 git 本身，任何未来 `git init` 都遵守，无需改任何 skill；置空即 opt-out。

### 开发内容概括

- 新增 `scripts/user-config.sh`：可 source 的库，提供 `ccg_user_config_path`（支持 `CCG_USER_CONFIG` 覆盖）/ `ccg_read_config`（安全解析，不 blind `source`）/ `ccg_seed_user_config`（user-wins seed）/ `ccg_apply_git_default_branch`。供 `install.sh` 与未来 hook/skill 复用。
- 新增 `user.config.example.env`：示例基线，首个 key `GIT_INIT_DEFAULT_BRANCH=master` + 注释。
- 改 `install.sh`：双轨部署后、调度器注册前 source 库并调用 seed + apply，`|| warn` 不阻塞主流程。
- 文档同步：项目 `CLAUDE.md`（目录结构 + 开发注意事项）、`README.md`（工作原理表 + Scripts 表 + 顶部清单）。

### 额外产物

- `docs/27-用户可配置项机制/verify-user-config.sh`：回归测试脚本（TDD 先行）。沙箱隔离（`CCG_USER_CONFIG` + `GIT_CONFIG_GLOBAL`），覆盖 T1 seed / T2 不覆盖 / T3 补缺追加 / T4 apply / T5 空值不写，**T1–T5 全绿**。
- `docs/27-用户可配置项机制/DESIGN.md`：Spike 的核心交付，沉淀完整机制设计 + 硬编码偏好盘点 + 后续 feat 拆分建议。

### 与计划的偏离

- **未改 `GLOBAL_AGENTS.md`**（计划原写「加一节简述机制」）：宪法是跨项目通用规则，「用户配置文件在哪/怎么读」是 claude-code-global 的实现细节，放项目 `CLAUDE.md` + `DESIGN.md` 更合适，避免污染通用宪法。本轮首例（git init 默认分支）宪法里本就没有硬编码，无需改宪法措辞。
- **验证脚本 T4/T5 用 `GIT_CONFIG_GLOBAL` 隔离**（计划写「重定向 HOME」）：`GIT_CONFIG_GLOBAL` 对全局 git 配置的隔离更精确，不受外部 `XDG_CONFIG_HOME` 干扰。

## 局限性

- 扁平 env 不支持嵌套/数组；当前所有候选偏好都是标量，够用。若未来出现结构化需求再评估升级。
- `ccg_apply_git_default_branch` 每次 `install.sh`（含 auto-update）都重新断言 `init.defaultBranch`；若用户绕过本机制用 `git config` 手改该键，下次同步会被改回配置文件的值。规避：把值写进 `~/.claude-code-global/config.env`（单一真源）或置空 opt-out。
- **真实完整 install 冒烟未在本轮跑**：从 worktree 跑 `install.sh` 会把全局软链指向临时 worktree（`/finish` 删 worktree 后悬空），且会真实注册 launchd。本轮以 `bash -n` 语法检查 + 沙箱隔离冒烟（真实 example + 默认逻辑路径 + 二次幂等）覆盖。**完整 install 冒烟应在 merge 回 master 后从主仓库跑一次**：
  ```bash
  bash install.sh
  git config --global init.defaultBranch   # 应输出 master
  ```

## 后续 TODO（派生 feat，/finish 时按需 /backlog 建 issue）

1. **commit trailer 署名可配置**：提取为配置键，并顺手修 `skills/commit/SKILL.md`（`Claude`）与 `GLOBAL_AGENTS.md:80`（`Claude Sonnet`）的署名不一致。这是「LLM 消费方读用户配置」的首个样例。
2. 视需要提取基础对话语言等其余偏好。
3. 若 skill 消费方增多，约定统一的「skill 读用户配置」措辞片段，避免每个 skill 重复描述读取逻辑。

## 可沉淀项

本仓库**就是** claude-code-global，按 `/finish` 自指守卫：跨项目资产候选不跨仓库 file，改走本地 `/backlog`。

1. **用户可配置机制的后续扩展**（commit 署名可配置、skill 读配置统一措辞）—— 属本仓库 feat，去向＝本地 `/backlog`，已列入「后续 TODO」第 1、3 条。
2. **bash `set -u` 下变量紧跟全角中文标点的坑**：`echo "...$var（"` / `$var，` 会把多字节标点并入变量名报 `unbound variable`，须用 `${var}` 定界。通用性够（任何写中文 `echo`/日志的 shell），但本轮仅 1 次出现，**暂记于此**；若后续再遇（≥2 次）再沉淀为 `rules/shell.md` 之类的领域规则，避免单点过早抽象。

> 收尾备注：本轮按作者要求**保留 `round27-用户可配置项机制` 分支、暂不合并 master**，issue #10 暂不关闭（BACKLOG 索引保留该行）。
