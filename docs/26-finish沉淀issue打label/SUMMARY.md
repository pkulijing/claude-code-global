# SUMMARY：跨项目沉淀 issue 缺 label 问题修复

## 开发项背景

`/finish` 的 Step 3 会在任意项目里反思「跨项目可沉淀流程」，并对跨项目资产候选**跨仓库提 issue 到 claude-code-global**。三轴 label（type / priority / area）是这类 issue 能被正确归类、检索的前提。

用户发现：通过其他项目沉淀到 claude-code-global 的改进 issue **可能缺少 label**，举例 [#12](https://github.com/pkulijing/claude-code-global/issues/12)（labels 为空），希望排查原因并优化 skill 描述，让这类 issue 可靠带上 label。

## 实现方案

### 关键设计

**根因（调查结论）**：

1. **远端 label 齐全**：claude-code-global 远端三轴 label 全部存在，所以 `/finish` 正常跑时不会因 label 缺失而创建失败。
2. **#12 的真实成因是「绕过 `/finish`」**：#12 创建于 finish Step 3.5 特性引入**之后**，但其 body 明说「非 `/start` `/finish` 闭环，所以单独沉淀」——是一次 wujie-data-format 的 review session 里**临时手动**提的跨仓库 issue，根本没走打 label 纪律。
3. **Step 3.5 路径本身仍有隐患**：`gh issue create --label X` 在 label 不存在时**整条失败**（非静默丢弃），而 Step 3.5 无任何兜底——agent 撞上报错后最自然的反应是去掉 label 重试以求成功，恰好产出无 label 的裸 issue。

**问题分层 → 对应修复**：

- **(B) `/finish` 之外的临时沉淀无纪律**（#12 直接成因）→ **helper 层加护栏**：唯一能拦住所有路径（含 ad-hoc 手动）的层级。
- **(A) Step 3.5 路径不够硬** → **加固 skill 描述**：创建前校验 + 失败绝不丢 label。

**职责分离**：helper 是 backlog/start/finish 通用工具，只强制「跨仓库创建 ≥1 label」（粒度通用、不误伤 in-repo 创建）；「必须恰好三轴」纪律留在 `/finish` skill 层。

**TDD**：护栏与 label-list argv 构造都抽成纯函数（`cross_repo_label_guard_error` / `build_label_list_cmd`），沿用 helper 既有的纯函数 self-test 风格——先加失败用例（红，`NameError`），再写实现（绿）。

### 开发内容概括

| 文件                        | 改动                                                                                                                                                                                                                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `scripts/platform_issue.py` | 新增 `cross_repo_label_guard_error`（跨仓库 `--repo` 且零 label → 拒绝，`--allow-no-label` 逃生）并接入 `cmd_issue_create`；新增 `build_label_list_cmd`，`cmd_label_list` 改用之并支持 `--repo`；`issue-create` 加 `--allow-no-label` flag、`label-list` 加 `--repo` flag；`cmd_self_test` 补 8 条用例 |
| `skills/finish/SKILL.md`    | Step 3.5 step 2 加「创建前 `label-list --repo` 校验三轴 label 存在、只从列表挑」；step 4 加失败兜底「绝不去掉 label 重试，改修 label 后重试，仍不行则报用户、不阻塞 finish」                                                                                                                           |
| `GLOBAL_AGENTS.md`          | 「issue 统一走 helper」那条补一句：跨仓库沉淀 issue 必须带三轴 label，helper 已强制拦截                                                                                                                                                                                                                |

### 额外产物

- helper `cmd_self_test` 新增 8 条用例（护栏 4 条 + `build_label_list_cmd` 4 条）。
- 回补历史遗留 **#12** 的三轴 label：`type:docs` + `area:doc` + `priority:P2`（既验证流程、又清理裸 issue）。

## 局限性

- helper 护栏只能拦住「经 helper 创建」的路径。若 ad-hoc agent 违反宪法直接调原生 `gh issue create`，仍可能裸提——但宪法已规定「统一走 helper」且本轮再加强化，结构上未为此额外造重型拦截（如 git hook）。
- helper 无 `issue-edit` / `label-add` 子命令，#12 补 label 用 `gh issue edit` 一次性手动完成（一次性维护动作，未为此扩 helper）。
- `~/.claude/scripts/platform_issue.py` 软链指向主检出，故护栏与新 flag 在**其他项目**的 `/finish` 里需待本轮合并到 master 后才生效（helper 与 skill 改动一并落地，一致）。

## 后续 TODO

- 若未来 ad-hoc 裸提仍频发，可考虑给 helper 加 `issue-edit` 子命令统一收口编辑类操作，并把「统一走 helper」从约定升级为更强的拦截。当前不做（触发面窄、宪法约定 + 护栏已够）。

## 可沉淀项

本轮即在 claude-code-global 仓库内开发，产出本身就是跨项目资产（helper 护栏 + finish 纪律 + 宪法约定），已直接落地到本仓库，**无需再向本仓库跨仓库提 issue**。

一条**方法论层面**的可复用经验：**「skill 软要求」与「工具硬护栏」要分层**——当某条纪律（如打 label）只写在 skill 描述里时，绕过该 skill 的路径（ad-hoc 调用）就完全不受约束；把底线约束下沉到被各路径共用的 helper/工具层，才能形成兜底。此经验已体现在本轮设计中，且与现有约定一致，按自指守卫不再额外 file，记此备查。
