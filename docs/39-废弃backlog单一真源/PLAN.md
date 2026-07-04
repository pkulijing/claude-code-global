# PLAN：废弃 docs/BACKLOG.md，云端 issue 单一真源

对应 [#40](https://github.com/pkulijing/claude-code-global/issues/40)。方案已拍板：**方向 A（彻底删 BACKLOG.md）+ 去处 (a)（4 条「刻意不做」各建带 `wontfix` 的 closed issue）**。

## 0. 关键事实（已探明）

- 平台 GitHub，slug `pkulijing/claude-code-global`。
- **唯一 open 项是 #7**，已是云端 issue，删 BACKLOG.md 不丢信息，saved query 天然覆盖。
- **`wontfix` label 远端已存在**，但本地 `.github/labels.yml` 缺 → 需补进本地真源（否则本地/远端 drift，正是本轮要消除的问题）。因远端已有，建 closed issue 时可直接用，无需先同步。
- 4 条「刻意不做」引用的 SUMMARY 全部存在（round 14 / 17 / 24 / 22）。
- `platform_issue.py` 中的 `backlog/start` 是调用方 skill 名，**非** BACKLOG.md 文件 → 不改。
- `bootstrap` / `start` / `sync-project-config` 里的 `/backlog` 是 skill 命令本身 → 保留。

## 1. Saved issue query 链接（速览入口，替代 BACKLOG.md）

统一采用「按 priority 过滤 open issues」的 GitHub query URL：

```
https://github.com/pkulijing/claude-code-global/issues?q=is%3Aissue+is%3Aopen+label%3Apriority%3AP0%2Cpriority%3AP1%2Cpriority%3AP2
```

（`label:priority:P0,priority:P1,priority:P2` 是「或」语义，命中任一即列出；`is:open` 限未关闭。）此 URL 挂到 README + GLOBAL_AGENTS.md。

> 注意 skill 内的骨架文本要保持「平台无关」——沿用 backlog SKILL 既有做法，用 `{slug}` / `detect-platform` 派生 GitHub / GitLab 两种 URL 形态的描述，不硬编码某一平台。本仓库 README/GLOBAL_AGENTS 是 GitHub 项目自身文档，可直接写死 GitHub URL。

## 2. 先建 4 个带 `wontfix` 的 closed issue（迁移「刻意不做」）

**先迁移、再删文件**——保证信息不丢。每条：

- `--title`：一句话概括「刻意不做的项」
- `--label wontfix` + `--label area:<Y>`（沿用原条目的 area）+ `--label priority:P2`（都是低优先「不做」项）+ `--label type:docs`（约定决策性质）
- body：原原因 + 引用原 SUMMARY 路径（写「当前真相」，不写 round-NN 到正文标题，但正文里保留「round N 决定」作为 WHY 上下文是允许的历史锚，符合 rules/python §3.4 的「历史标记作为 WHY 的一部分」例外）
- 建完立即 close（`gh issue close` / helper 若无 close 子命令则建后手动 close）

4 条：

| #   | 标题（拟）                                    | area          | 原 SUMMARY                        |
| --- | --------------------------------------------- | ------------- | --------------------------------- |
| 1   | 平台双兼容不引入「对端死文件清理」opt-out     | area:template | docs/14-.../SUMMARY.md §5.3       |
| 2   | python-uv 模板不内置 torch/aliyun wheels 索引 | area:template | docs/17-.../SUMMARY.md 关键设计#8 |
| 3   | 不再追求「会话标题携带轮次」能力              | area:skill    | docs/24-.../SUMMARY.md            |
| 4   | Codex 双装端到端实测不再追踪                  | area:install  | docs/22-.../SUMMARY.md §局限性    |

先确认 helper 是否支持 `issue-close`；不支持则用 `gh issue close <N> -r "not planned"`（GitHub 端），这一步仅本仓库执行、可直接用 gh。

## 3. `.github/labels.yml`：补 `wontfix`（消 drift）

在文件末尾追加（远端已有此 label，补进本地真源使二者一致）：

```yaml
- name: "wontfix"
  color: "FFFFFF"
  description: "刻意决定不做的项（decided-no），带原因归档为 closed issue"
```

（color 取 GitHub 默认 wontfix 的白灰系；若远端已有具体色值，以远端为准对齐——建 issue 前 `label-list` 可顺带核对。）

## 4. 删除 `docs/BACKLOG.md`

`git rm docs/BACKLOG.md`。

## 5. `skills/backlog/SKILL.md` 重构

- **frontmatter description**：去掉「+ 在 docs/BACKLOG.md 索引中加一行链接」，改为仅「创建 issue（含三轴 label）」。
- **开头职责段**：从「完成两件事」改为「完成一件事：创建 issue」。删掉「`docs/BACKLOG.md` 退化为扁平索引」的描述。
- **Step 6 标题**：`执行 —— 创建 issue + 加 BACKLOG 索引` → `执行 —— 创建 issue`。
- **删 Step 6.2**（BACKLOG.md 骨架初始化）整节。
- **删 Step 6.3**（追行）整节。
- **Step 7 反馈**：去掉「BACKLOG.md 中追加的位置」，改为只打印 issue URL + 提示「open issues 速览见 saved query（附链接）」。
- **删除职责说明**（开头第 12 行「删除职责仍在 /finish...删 BACKLOG.md 那行」）：改为「issue 关闭仍由 /finish 的 `Closes #N` 完成」，去掉删 BACKLOG 行的表述。

## 6. `skills/finish/SKILL.md` 重构

- **frontmatter description**：去掉「更新 BACKLOG.md」。
- **Step 2「扫 SUMMARY 提示不再追踪段补录」**：这是失去落点的核心步骤。重构为——扫 SUMMARY「局限性 / 后续 TODO」，问用户「有没有刻意决定不做的项要归档？」；有 → **引导用户走 `/backlog` 起 issue 并加 `wontfix` label 后 close**（或直接在本步用 helper 建带 `wontfix` 的 issue 再 close），不再写 BACKLOG.md「不再追踪」段。措辞对齐「issue 是真源」。
- **Step 3 内 BACKLOG 措辞**（41 / 62 / 91 / 106 行）：
  - 41「不进任何 BACKLOG 索引」→ 改为「不进任何本地索引（本项目无 BACKLOG.md 亦无妨）」或直接简化，保留「跨仓库沉淀 issue 独立于当前项目」的语义。
  - 62 自指守卫「issue 进 BACKLOG」→ 改为「走本地 `/backlog` 起 issue」（去掉「进 BACKLOG」）。
  - 91 body 末尾标注「未进 BACKLOG」→ 改为「跨项目自动沉淀 issue」。
  - 106「不更新任何 BACKLOG.md」→ 该行可删（BACKLOG.md 已不存在，无需强调不更新）或保留为「不更新任何本地索引」。
- **Step 4:124「从 docs/BACKLOG.md 删除对应行」**：删掉这一子项（issue 由 `Closes #N` 自动关，无需删 BACKLOG 行）。
- **Step 6:157 判定数据源「明示忽略 BACKLOG.md 自身」**：去掉 `BACKLOG.md`（不再有此文件）。
- **Step 7:168**：去掉「本次 BACKLOG.md」于 commit 变更清单的描述。

## 7. `GLOBAL_AGENTS.md`「需求管理」章重构（3 处）

- 第 42 行「`docs/BACKLOG.md` 是未关闭 issue 的扁平索引」→ 替换为「未关闭 issue 的速览由 **saved issue query**（按 priority 过滤 open issues）承担，README 挂链接；无本地索引文件」。
- 第 44 行「`/backlog` 建 issue + 写 BACKLOG 索引」→ 「`/backlog` 建 issue」。
- 第 46 行「已完成项不在 BACKLOG.md 追踪...「不再追踪」段只记刻意不做的项」→ 改为「**刻意决定不做**的项归档为带 `wontfix` label 的 closed issue（可检索、可过滤），不再维护本地文件段」。

## 8. `README.md` 重构（4 处）

- 第 5 行「详见下文 Backlog 与开发项管理」→ 保留指向，措辞改为 issue 单一真源。
- 第 80 行能力表「`docs/BACKLOG.md` 仅作未关闭 issue 的扁平索引」→ 「未关闭 issue 速览走 saved query（按 priority 过滤）」。
- 第 91 行 `/backlog` 描述「并在 docs/BACKLOG.md 索引中加一行」→ 删掉后半句。
- 第 93 行 `/finish` 描述「更新 BACKLOG.md」→ 删掉。
- 第 195/197 行「Backlog 与开发项管理」段：把「`docs/BACKLOG.md` 是扁平索引」替换为 saved query 链接说明；工作流描述保持不变（三件套仍在）。

## 8.5 `skills/sync-project-config/SKILL.md`：老项目遗留 BACKLOG.md 一次性迁移（执行中追加）

> 执行阶段用户提出的关键补充：本轮删的是 claude-code-global 自己的 BACKLOG.md，但**其他已有 `docs/BACKLOG.md` 的老项目**不会自动迁移，会留下「约定说无本地索引、现实里文件还在」的 drift。经确认，迁移逻辑落 **`/sync-project-config`**（而非 `/finish`）——它的本职就是「把 claude-code-global 的约定变更同步进老项目」，语义正好、触发时机对（老项目本就为拉新约定跑它），且不给每轮 `/finish` 加无谓探测。

在「模式判断」之前加一节「废弃 BACKLOG.md 一次性迁移」（类比既有「旧名 marker 自动迁移」的一次性、幂等定位）：

- 探测项目根 `docs/BACKLOG.md`，不存在 → 跳过（幂等）。
- 存在 → 引导：open 项逐条确认已有云端 issue（BACKLOG 行本就带链接）；「刻意不做」项逐条建带 `wontfix` 的 closed issue（复用 `/finish` Step 2 手法）；两类迁完 `git rm docs/BACKLOG.md`；再继续正常 sync。
- README skill 表 `/sync-project-config` 描述补一句「+ 废弃 BACKLOG.md 一次性迁移」。

## 9. 验证（无代码逻辑，靠 grep 兜底）

删改完成后，全仓（排除 `docs/`）grep 残留悬空引用：

```bash
grep -rn -i "BACKLOG" . --include="*.md" --include="*.sh" --include="*.py" \
  | grep -v "/docs/" | grep -v "platform_issue.py"
```

期望只剩 `platform_issue.py` 里的 skill 名注释（`backlog/start`）—— 那不是 BACKLOG.md 文件，合法保留。其余任何 `BACKLOG.md` 字样都应清零。

另跑一次 `install.sh`？——本轮无 skill 增删、无 hook 增删、无 settings/base 改动（仅改 skill 文本 + 文档 + labels.yml），按 CLAUDE.md「修改 skill 内容无需重装」，**不需要**重跑 install.sh。labels.yml 是模板文件、软链生效，改内容也无需重装；远端 label 同步走 `/sync-project-config` 或 helper `label-sync-from-file`（本轮远端已有 wontfix，可省）。

## 10. 收尾

`/finish`：写 SUMMARY → 反思可沉淀项（自指守卫走本地 /backlog）→ README review（本轮命中「面向用户的工作流改动」触发，README 已在本轮改过）→ /devtree → /commit（`Closes #40`）→ worktree 收尾（rebase → FF merge → 清理）。

## 执行顺序

1. 补 `.github/labels.yml` 的 `wontfix`（§3）
2. 建 4 个带 `wontfix` 的 closed issue（§2）——先迁移信息
3. 删 `docs/BACKLOG.md`（§4）
4. 改 4 处文本：backlog SKILL（§5）、finish SKILL（§6）、GLOBAL_AGENTS.md（§7）、README.md（§8）
5. grep 验证无悬空引用（§9）
6. `/finish` 收尾（§10）

> 无自动化测试可写（纯约定/文档 + skill 文本），验证靠 §9 的 grep 兜底 + 人工 review skill 文本连贯性。
