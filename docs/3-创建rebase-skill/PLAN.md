# 实现计划：创建 rebase skill

## 方案

在 `skills/rebase/` 下创建 `SKILL.md`，定义一个"诊断 + 分段清单"的 rebase 流程。skill 本身不直接执行 rebase，而是引导 CC 按固定步骤读状态、给建议、等确认、再执行。

## SKILL.md 结构设计

分为四个阶段，每个阶段结束都要等人类确认再进入下一阶段。

### 阶段 0：诊断当前状态（仅本地）

**本 skill 只处理本地分叉，不涉及 fetch / 远程同步。** 如果分叉来自远程，人类需要先自行把远程 pull 到本地后再调用。

执行并展示：

- `git rev-parse --show-toplevel` 和 `git worktree list` — 确认当前是否在 worktree 内，是哪一个
- `git branch --show-current` — 当前分支
- `git status` — 工作区/暂存区是否干净
- `git log --graph --oneline --all -20` — 可视化本地分叉
- 让 CC 根据结果判断：rebase 方向（谁 rebase 到谁）、分叉 commit 数、是否有未提交改动需要先处理

输出"诊断报告"，等人类确认 rebase 方向。

### 阶段 1：前置检查与备份

**强制项**：

- 工作区必须干净。不干净则先要求 commit 或 stash，不允许直接 rebase。
- 打备份 tag：`git tag backup/<branch-name>-<YYYYMMDD-HHMM>`，告诉人类"如果 rebase 搞砸了，用 `git reset --hard <tag>` 回到此刻"。
- base 分支的状态以本地为准（不 fetch、不 pull）。

等人类确认后进入下一阶段。

### 阶段 2：执行 rebase 与冲突处理

- 执行 `git rebase <base>`
- 若无冲突，直接到阶段 3
- 若有冲突：
    - 用 `git status` 列出冲突文件
    - 逐个文件处理，不要一次改完
    - 每解决一个文件后 `git add <file>`，所有文件解决完跑 `git rebase --continue`
    - 提醒人类：任何时候可以 `git rebase --abort` 撤销整个 rebase，回到 rebase 前的状态（备份 tag 作为二重保险）
- 重复处理，直到 rebase 完成

完成后展示 `git log --graph --oneline -10`，让人类肉眼验证历史正确。

### 阶段 3：合并到目标分支 / 推送 / 验证

rebase 完成后，**合并一律用 fast-forward**（`--ff-only`），严禁生成 merge commit：

- 切到合并目标分支（通常是 master），`git merge --ff-only <rebased-branch>`
- 若 `--ff-only` 失败，说明目标分支还有新 commit，回头把这些 commit 再 rebase 到 rebased-branch 上，保持直线历史。**绝不 fallback 到普通 merge。**

推送（如有需要）：

- 被 rebase 过的分支若已推送过远程，推送时统一用 `git push --force-with-lease origin <branch>`，禁用 `git push --force`
- master 这类 FF 推上去的分支正常 `git push` 即可

验证：

- 跑测试或启动服务确认功能未坏
- 确认无误后，可删除阶段 1 打的备份 tag（`git tag -d backup/...`）

## 额外写入 SKILL.md 的原则

- **所有合并必须 FF**：严禁产生 merge commit，历史保持直线。
- **只处理本地**：skill 不 fetch、不 pull；远程同步由人类先手动处理。
- **个人分支才 rebase**：公共分支（master/main、已有别人 review 的 PR 分支）不 rebase。
- **数据优先于直线历史**：rebase 过程中若出现无法处理的状态，宁可 `--abort` 回退备份 tag，也不强行推进。

## 涉及文件

- 新建：`skills/rebase/SKILL.md`
- 无需改 `install.sh`（脚本通过 `skills/` 下的目录列表自动链接，新增目录重跑即可）

## 验证

- 运行 `bash install.sh` 确认 `~/.claude/skills/rebase/` 符号链接建立
- 在当前 whisper-input 的分叉场景下调用 `/rebase`，验证流程是否真的把人类一步步带到安全终点
- 事后把实际遇到的"清单没覆盖到的坑"补回 SKILL.md

## 开放问题

1. 交互式 rebase (`-i`)：一期不支持，先把"直线 rebase 到新 base"打磨好。
2. 合并策略已明确：**一律 FF，不考虑 merge**。
