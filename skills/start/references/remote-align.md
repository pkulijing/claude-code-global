# 开轮远端对齐（`/start` 通用流程第 1 步展开）

> `/start` **issue 驱动轮**在通用流程第 1 步读本文；自由描述轮撞车检查整体不适用，只跑一条 `git fetch origin`。

**为什么**：多设备 + 云端 routine 并行的仓库里，「这个需求远端早就做完了」是常态而非意外。`/start` 若完全不碰远端，撞车只会在 `/finish` 之后才暴露 —— 那时一整轮的开发与 review 已经付过钱了。（真实代价：一次完整实现 + 2 轮 review + 2 个 commit 全部作废，而远端版本还更全面。）

三步，**任何一步失败都不许阻断开轮**：

1. **`git fetch origin`** —— 只更新 remote-tracking，不动工作区、不动本地分支，安全。下面几条命令里的 `<主分支>` 按 `references/worktree-create.md` 首条的方法探测（探一次，两处复用）。
2. **issue 驱动时，查这条是不是已经被做掉了**（自由描述分支跳过本步）：

   ```bash
   # ① issue 自身状态：走平台 API，不依赖 fetch 是否成功
   python3 $HOME/.claude/scripts/platform_issue.py issue-view <N>   # 读 state / stateReason
   # ② 关闭它的 commit —— 已合入主分支的
   git log origin/<主分支> -i -E \
       --grep '(^|[^a-z])(close[sd]?|fix(es|ed)?|resolve[sd]?) #<N>([^0-9]|$)' \
       --format="%h %ad %s" --date=short
   # ③ 同上，但只看远端在途分支（PR 已开、尚未合入）
   git log --remotes=origin --not origin/<主分支> -i -E \
       --grep '(^|[^a-z])(close[sd]?|fix(es|ed)?|resolve[sd]?) #<N>([^0-9]|$)' \
       --format="%h %ad %s" --date=short
   ```

   **这次 `issue-view` 就是「issue 驱动分支」第 1 步那一次调用，别调两遍。**

   **`--grep` 是子串匹配，两侧边界都不能省**（下面两条都是实测，别「简化」掉）：

   - **右边界 `([^0-9]|$)`** 挡住「查 `#11` 命中 `Closes #114`」—— 越小号的 issue 越容易被无关 commit 拦住。
   - **左边界 `(^|[^a-z])` + 按 GitHub 真实关键字清单枚举的动词**挡住语义相反的句子。写成 `(clos|fix|resolv)[a-z]*` 时，`still unresolved #11` 与 `not fixing #11` **都会命中** —— 把「还没修」报成「已经修完了」。GitHub 认的关闭关键字只有 close/closes/closed、fix/fixes/fixed、resolve/resolves/resolved，**没有进行时**，别用 `[a-z]*` 一把抓。

   **为什么三个信号都要**：`state` 是平台权威、且**不依赖提交信息约定** —— `/start` 要在任何项目里跑，别的项目未必写 `Closes #N`，那里 ②③ 恒为空。而 ②③ 给的是**证据**（谁做的、哪个 commit、什么时候），正是人类拍板时要看的。③ 单独存在是因为「远端分支上已经做完、PR 还开着、issue 也还 open」这类撞车 ①② 都看不见 —— 本仓 `/routine-dev` 每周开 PR 却不自动合，正是这个形态。

3. **任一命中 → 停下报告，等人类拍板**，别自己决定继续还是放弃：

   ```
   ⚠ #<N> 看起来已经被做过了：
     - issue 状态：closed（COMPLETED，2026-08-01）
     - 关闭它的 commit：735c04c 2026-08-02 fix(review-loop): …（已在 origin/master）
   选项：① 不做了（本轮取消）② 只补真增量（说明差在哪）③ 远端做得不对，重做（说明哪不对）
   ```

   **`stateReason` 是 `NOT_PLANNED` 必须单独说清**：那不是「已经做完了」，是**有人决定不做**，两者的处理方向完全相反。

**降级：三条独立的失败路径，都只提示、不阻断**

| 失败 | 处理 |
| --- | --- |
| 没有 `origin` remote（纯本地仓） | 跳过整个远端对齐，一行提示，继续 |
| `git fetch` 失败（离线 / 无权限 / 超时） | 跳过编号 ④⑤ 与 ②③，**明确打印**「远端对齐已跳过：<原因>；轮次编号与撞车检查仅基于本地信号」，继续 |
| `issue-view` 拉不到 | 照既有行为处理，不因新增的 `state` 检查而变严 |

① 走平台 API、②③ 走 git，**两条路互相独立**：一个挂了另一个照跑，别因为 fetch 失败就连 `state` 也不查了。

**撞车已经发生之后怎么办**（本地写完了才发现）不归 `/start` 管 —— 判据在宪法「执行」段的停机义务里。
