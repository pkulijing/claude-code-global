# PROMPT：跨项目沉淀 issue 缺 label 问题修复

## 背景

`/finish` 的 Step 3 会在任意项目里反思「跨项目可沉淀流程」，并对跨项目资产候选**直接向 claude-code-global 仓库跨仓库提 issue**（Step 3.5）。这类 issue 是把分散经验固化成全局资产的关键入口，因此**三轴 label（type / priority / area）是它能被检索体系正确归类的前提**。

用户发现：通过其他项目沉淀到 claude-code-global 的改进 issue **可能缺少 label**，举例 [#12](https://github.com/pkulijing/claude-code-global/issues/12)（labels 为空）。希望排查原因并优化 skill 描述，让这类 issue 可靠地带上 label。

## 现状调查结论

1. **远端 label 齐全**：claude-code-global 远端三轴 label（`type:*` / `priority:*` / `area:*`）全部存在。所以 `/finish` 正常按 Step 3.5 跑时，`gh issue create --label` 不会因 label 缺失而失败。
2. **#12 的真实成因是「绕过 `/finish`」**：#12 创建于 2026-05-28（晚于 finish Step 3.5 特性引入的 2026-05-21），但其 body 明确写「本批 lessons 来自一次 wujie-data-format 项目的 code review session（非 `/start` `/finish` 闭环，所以单独沉淀）」。即它是一次 review session 里**临时手动**提的跨仓库 issue，**根本没走 Step 3.5 的打 label 纪律**。
3. **Step 3.5 路径本身仍有隐患**（即便走了正路也可能漏 label）：
   - `gh issue create --label X` 在 label 不存在于目标仓库时会**整条创建失败**（非静默丢弃）。Step 3.5 当前**无任何错误兜底**——agent 撞上「label not found」报错后，最自然的反应是去掉 label 重试以让创建成功，结果产出无 label 的 issue。
   - helper 的 `label-list` 命令**不支持 `--repo`**，无法在创建前对**目标（跨）仓库**校验 label 是否存在。Step 3.5 step 2 让 agent「读 `$GLOBAL_DIR/.github/labels.yml`」选 label，但 labels.yml 是真源文件、未必已同步到远端，二者可能脱节。

## 问题分层

- **(A) `/finish` Step 3.5 路径不够硬**：缺 label 存在性校验、缺创建失败兜底，导致即便走正路也可能在 label/远端脱节时悄悄丢 label。
- **(B) `/finish` 之外的临时跨仓库沉淀无纪律**：像 #12 这种在 review session 里手动提的沉淀 issue，完全不经过 Step 3.5，没有任何打 label 约束——这是 #12 的直接成因。

## 目标

优化相关 skill 描述（必要时配合 helper / 文档），让**跨项目沉淀到 claude-code-global 的 issue 可靠带上三轴 label**：

1. 加固 `/finish` Step 3.5：让「打 label」从「软要求」变成「带校验 + 失败显式暴露、绝不悄悄丢 label」的硬流程。
2. 针对 (B)：为「`/finish` 之外的临时跨仓库沉淀」提供一条有 label 纪律的标准路径（复用同一套 label 选择 + 校验逻辑），避免再出现 #12 这类裸 issue。
3. 顺手补打 #12 的 label（既是验证，也是清理历史遗留）。

## 约束与边界

- **自指守卫**：本轮就在 claude-code-global 仓库内开发；Step 3.5 的自指守卫（当前仓库即 claude-code-global 时改走本地 `/backlog`）逻辑不能被破坏。
- 改 skill 描述为主，**不过度工程化**；若需动 helper（如让 `label-list` / `issue-create` 支持跨仓库校验），改动要小而稳，并补 self-test。
- 遵循「文档一律中文」「skill 增减才触发 README review」等全局规范。
- 具体落点与是否动 helper 在 PLAN.md 中定夺并经用户确认后再写代码。

## 待决问题（PLAN 阶段澄清）

- (B) 的标准路径落在哪里？（新增独立 skill / 在 finish 抽一段可复用说明 / 仅写进 GLOBAL_AGENTS.md 一条约定）
- 是否需要让 helper 的 `label-list` 支持 `--repo` 以做跨仓库 label 校验，还是 skill 层用 `gh label list --repo` 直接校验即可。
