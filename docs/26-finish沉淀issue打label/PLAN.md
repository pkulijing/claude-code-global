# PLAN：跨项目沉淀 issue 缺 label 问题修复

## 方案总览（经用户确认的方向）

- **(B) helper 层加护栏**：`platform_issue.py issue-create` 在「跨仓库（`--repo`）且零 label」时**拒绝创建并报错**，提供 `--allow-no-label` 显式逃生舱。这是唯一能拦住所有路径（含 `/finish` 之外的 ad-hoc 手动提交）的层级。
- **(A) 加固 `/finish` Step 3.5 描述**：增加「创建前用 `label-list --repo` 校验 label 存在性」+「创建失败绝不悄悄丢 label」两条硬约束。
- 辅助：让 helper `label-list` 支持 `--repo`，使跨仓库 label 校验成为可能（小而稳，配 self-test）。
- 补打历史遗留 **#12** 的三轴 label：`type:docs` + `area:doc` + `priority:P2`。
- 全局宪法 `GLOBAL_AGENTS.md` 现有「issue 操作统一走 helper」规则末尾补一句：跨仓库沉淀 issue 必须带三轴 label（helper 已强制）—— 一句话原地强化，不新增段落。

## 关键设计

### 1. helper 护栏只认「≥1 label」，不认「必须三轴」

helper 是通用工具（backlog / start / finish 共用）。把「必须恰好三轴」写进 helper 太死板，且 backlog/start 的 in-repo 创建语义不同。因此：

- **helper 层规则**：跨仓库（`--repo` 非空）创建必须 `≥1` 个 `--label`，否则拒绝。这刚好拦住 #12 那种「零 label 裸 issue」。
- **「必须三轴」纪律**留在 `/finish` Step 3.5 的描述里（skill 层），职责分离：helper 通用、skill 专用。

backlog 的 `issue-create` **不带 `--repo`**（in-repo），护栏不触发；现状零回归。

### 2. 护栏与 label-list 都抽成纯函数，便于 self-test

helper 现有 `cmd_self_test` 是纯函数测试（不起子进程）。沿用此风格：

- 新增纯函数 `cross_repo_label_guard_error(repo, labels, allow_no_label) -> str | None`：返回非空错误串表示应拦截，`None` 表示放行。`cmd_issue_create` 调它，非 None 则写 stderr 并 `return EXIT_ERROR`。
- 新增纯函数 `build_label_list_cmd(platform, repo) -> argv`（仿现有 `build_issue_create_cmd`）：把 `cmd_label_list` 里两分支的 argv 构造抽出来，支持尾随 `--repo`。`cmd_label_list` 改为 `_run(build_label_list_cmd(plat, args.repo))` 后再按平台解析输出。

### 3. 自指守卫不受影响

本轮在 claude-code-global 仓库内开发，但改的是「别的项目跑 `/finish` 时的行为」。Step 3.5 的自指守卫（当前仓库即 claude-code-global → 改走本地 `/backlog`、不 API 自 file）逻辑**原样保留**，护栏与校验只作用于真正发生跨仓库创建的场景。

## 改动清单

| 文件                        | 改动                                                                                                                                                                                                                                                                                      |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/platform_issue.py` | ① 新增纯函数 `cross_repo_label_guard_error`；② `cmd_issue_create` 平台检查后调用护栏；③ `issue-create` 子命令加 `--allow-no-label` flag；④ 新增纯函数 `build_label_list_cmd`，`cmd_label_list` 改用之并支持 `--repo`；⑤ `label-list` 子命令加 `--repo` flag；⑥ `cmd_self_test` 补对应用例 |
| `skills/finish/SKILL.md`    | Step 3.5 step 2/4 加固：创建前 `label-list --repo "$SLUG"` 校验三轴 label 都在目标仓库存在；强调三轴为**硬要求**（helper 已强制 ≥1）；创建失败（如 label not found）**绝不去掉 label 重试**，而是修 label（`label-sync-from-file` 同步或改选已存在 label）后重试，必要时停下报给用户      |
| `GLOBAL_AGENTS.md`          | 「需求管理」末尾「issue 操作统一走 helper」那条，补一句：跨仓库沉淀 issue 必须带三轴 label（helper 已内置零-label 护栏）                                                                                                                                                                  |
| 运行时动作                  | 补打 #12 标签：`type:docs` + `area:doc` + `priority:P2`（经 helper / `gh issue edit`）                                                                                                                                                                                                    |

## TDD：先写测试用例（红 → 绿）

执行阶段先把以下用例加进 `cmd_self_test`（会失败），再写实现让其通过。运行：`python3 scripts/platform_issue.py --self-test`（**跑 worktree 内副本**，因 `~/.claude/scripts` 软链指向主检出）。

**护栏 `cross_repo_label_guard_error(repo, labels, allow_no_label)`：**

| 输入                            | 期望            | 说明                                 |
| ------------------------------- | --------------- | ------------------------------------ |
| `("o/x", [], False)`            | 非 None（拦截） | 跨仓库零 label → 拒绝（#12 场景）    |
| `("o/x", ["type:feat"], False)` | `None`（放行）  | 跨仓库有 label → 正常                |
| `("o/x", [], True)`             | `None`（放行）  | 显式逃生舱                           |
| `(None, [], False)`             | `None`（放行）  | in-repo（backlog/start）不受护栏约束 |

**`build_label_list_cmd(platform, repo)`：**

| 输入              | 期望 argv                                               |
| ----------------- | ------------------------------------------------------- |
| `(GITHUB, None)`  | `["gh","label","list","--json","name","-q",".[].name"]` |
| `(GITHUB, "o/x")` | 上一行 + `["--repo","o/x"]`                             |
| `(GITLAB, None)`  | `["glab","label","list","--output","json"]`             |
| `(GITLAB, "o/x")` | 上一行 + `["--repo","o/x"]`                             |

`build_issue_create_cmd` 现有用例不变（护栏在 `cmd_issue_create` 层、不改 argv 构造）。

## 验证步骤

1. `python3 scripts/platform_issue.py --self-test` 全绿。
2. 手验护栏：`issue-create --repo <slug> --title T --body-file <f>`（无 label）→ 报错退出；加 `--allow-no-label` → 放行（**不真建 issue，用 `--debug` 看 argv 或 dry 验证逻辑**，避免污染远端）。
3. 手验 `label-list --repo <slug>` 能列出目标仓库 label。
4. 补打 #12 label 后，`issue-view 12` 确认 `labels` 含三轴。
5. 通读 Step 3.5 改后描述，确认自指守卫与逐条确认流程未被破坏。

## 局限性 / 不在本轮范围

- helper 护栏只能拦住「经 helper 创建」的路径。若 ad-hoc agent 违反宪法直接调原生 `gh issue create`，仍可能裸提 —— 但宪法已规定「统一走 helper」，本轮再加一句强化，结构上不再额外加硬约束（不值得为此造 git hook 等重型拦截）。
- 不改 backlog/start（它们 in-repo + 恒传三轴，无回归风险，无需动）。
