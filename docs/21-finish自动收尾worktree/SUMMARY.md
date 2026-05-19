# SUMMARY — Round 21：worktree 化的可并行开发工作流

## 开发项背景

issue [#9](https://github.com/pkulijing/claude-code-global/issues/9) 提出：Round 20 首次完整在 worktree 内走 round 后发现，`/finish` 跑完用户还要手工「调 `/rebase` → 解冲突 → `git merge --ff-only`」「`git worktree remove` + `git branch -d` + `git tag -d`」两组动作，三步走、每步一次人机往返。希望 `/finish` 自动识别 worktree 并一站式收尾。

计划阶段用户把范围从「只改 `/finish`」扩展为**把整个开发工作流改造成基于 worktree 的可并行流程**：`/start` 也默认为每轮开发创建独立 worktree，与 `/finish` 的自动收尾形成开闭对称。

## 实现方案

### 关键设计

1. **方向 A 内联，而非硬调用 `/rebase`**：计划阶段分析发现 `/rebase` 阶段 3 的 `git checkout <主分支>` 在 worktree 下**必失败**——主分支已被主工作树 checkout 占用（实测 `fatal: 'master' is already used by worktree at ...`）。故 `/finish` Step 5 自描述完整收尾流程、遵循 `/rebase` 的核心原则（FF-only、备份 tag、冲突逐文件解、abort 兜底），但不硬调用 `/rebase` skill。

2. **worktree-aware FF merge**：FF 合并改用 `git -C <主工作树> merge --ff-only <feature 分支>`，在主工作树上下文里合并，绕开「当前 worktree 无法 checkout 主分支」。主工作树路径由 `dirname "$(git rev-parse --path-format=absolute --git-common-dir)"` 算得。

3. **worktree 检测**：`git rev-parse --git-dir` 与 `--git-common-dir` 是否相等——主工作树两者都是 `.git`，linked worktree 下 `--git-dir` 为 `.git/worktrees/<name>`。

4. **cwd 自毁规避**：清理前必须先 `cd <主工作树>`，否则 `git worktree remove` 删掉 CC 脚下目录会让后续 Bash 失效。

5. **开闭对称 + 逃生舱**：`/start` 默认建 `.claude/worktrees/round<N>-<描述>/` worktree + 同名分支；`--no-worktree` 开关跳过、在当前分支直接干。`/finish` 检测非 worktree（含 `--no-worktree` round）即跳过收尾，对称无悬空分支。

### 开发内容概括

- **`skills/start/SKILL.md`**：新增 `--no-worktree` 开关；「通用流程」重排为 7 步并加「worktree 创建」小节（探测主分支 / 防嵌套 / 补 gitignore / `git worktree add` / cd 进入 / 告知用户）。
- **`skills/finish/SKILL.md`**：新增 **Step 5 worktree 收尾**（5.1 诊断 → 5.2 备份+rebase → 5.3 FF merge → 5.4 二次确认清理 → 5.5 不自动 push），原 Step 5 顺延为 Step 6。
- **`.claude/.gitignore`**（新建）：忽略 `worktrees/`，避免主工作树把嵌套 worktree 当 untracked。
- **`GLOBAL_CLAUDE.md`**：「核心开发模式」加一句简述——每轮默认在独立 worktree 进行、支持并行。
- **`README.md`**：更新 `/start`、`/finish` 的描述以反映 worktree 工作流。

### 额外产物

- 计划阶段在临时 worktree 中实测验证了关键 git 命令：`--git-dir`/`--git-common-dir` 区分、`dirname` 取主工作树路径、`git checkout master` 在 worktree 下失败、`git -C <主工作树> merge --ff-only` 从 feature worktree 内执行成功、`git worktree remove`+`git branch -d` 清理（测试提交已 `reset --hard` 回滚）。

## 局限性

- **Round 21 自身未走新工作流**：本轮 `/start 9` 已在 master 主工作树启动，且 `~/.claude/skills/*` 软链指向主工作树文件（worktree 分支内改 skill 不即时生效），故新流程从 Round 22 起才生效——「创建工作流的那一轮无法自举」。
- **未做活体集成测试**：产物是 skill 指令文档（markdown），无自动化单测；仅做了 dry-run 分支走查 + 关键 git 命令实测，全流程要等 Round 22 首个真实 worktree round 才被完整验证。
- **`/rebase` 未改造**：worktree 场景的 rebase+merge 由 `/finish` Step 5 自带，`/rebase` 阶段 3 仍只支持非 worktree 的 checkout+merge；两处逻辑有部分重叠。
- **Chinese 分支名**：worktree/分支命名沿用 docs 目录的中文描述，依赖 git UTF-8 支持，未在异常文件系统环境验证。

## 后续 TODO

- Round 22 作为首个真实 worktree round，重点验证 Step 5 全流程（尤其 rebase 冲突暂停、FF merge、清理确认/拒绝、`worktree remove` 失败提示）。
- 若未来发现 `/finish` Step 5 与 `/rebase` 重叠逻辑维护成本偏高，再考虑把 `/rebase` 阶段 3 改造成 worktree-aware 以真正复用。
