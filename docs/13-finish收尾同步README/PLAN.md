# PLAN：/finish 收尾时同步 review/更新 README

## 方案

走 issue body 倾向的**方向 B（清单触发）**：仅当本轮变更命中预设清单才进入 README review；纯内部重构 / bug fix / 文档微调不触发。

## 在 `/finish` 中的位置

在现 Step 3（`/devtree`）与 Step 4（`/commit`）之间插入 **Step 3.5：README review & update**，编号不重排。

理由：

- SUMMARY / 不再追踪 / BACKLOG / devtree 都是元数据/索引，README 更接近用户视角入口
- devtree 不会改 README，无副作用
- 仍在 commit 前 → README 改动跟本轮代码进同一 commit

## 触发条件清单（写到 SKILL.md）

满足任一即触发：

1. `skills/<name>/` 子目录新增或删除
2. `hooks/*.sh` 新增或删除
3. 顶层目录结构变化（仓库根目录、`skills/` / `templates/` / `hooks/` 这几层出现新增/删除子目录）
4. **面向用户的工作流改动**：本轮 PROMPT.md 或 SUMMARY.md 中明示「面向用户的入口/约定改了」（例：BACKLOG / issue 驱动、安装方式、模板使用方式）

明示**不触发**：

- 纯内部重构（重命名变量、抽函数）
- bug fix
- 与 README 无关的文档微调（仅改 docs/ 下的开发记录）
- 依赖升级

## 判定数据源

- `git status --porcelain` + `git diff --cached --name-status` 的并集（本步在 commit 前跑）
- **明示忽略**前面几步刚改的 `SUMMARY.md` / `DEVTREE.md` / `BACKLOG.md` 自身

## 触发后子步

1. 读 `README.md` + 本轮 `PROMPT.md` / `SUMMARY.md`
2. 列出 README 中需要新增 / 修改的具体段落（不动无关段落）
3. 直接 Edit README.md
4. 一句话告知用户改了什么

## README 基线一次性补齐

当前漂移盘点（已通过 `ls skills/ hooks/ templates/` 与 `install.sh` 核对）：

| 漂移项       | 当前 README 状态                    | 应补内容                                                                                                                      |
| ------------ | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Skills 段    | 只列 `/start /finish /commit`       | 补 `/backlog` `/bootstrap` `/clean-local-setting` `/devtree` `/pybump` `/rebase` `/sync-project-config`，简洁列表（一行一条） |
| Hooks 系统   | 完全没提                            | 新增「Hooks」段：`hooks/fix-after-edit.sh`，由 install.sh 软链                                                                |
| 模板系统     | 完全没提                            | 新增「跨项目共享模板」段：`templates/_common/` + stack（`python-uv`），由 `/bootstrap` `/sync-project-config` 使用            |
| 工作原理表   | 缺 hooks/templates/global-repo 三行 | 补三行（部署方式见 install.sh）                                                                                               |
| 顶部一句话   | 没提 hooks/templates                | 加上                                                                                                                          |
| 开发模式指针 | 没提                                | 加一句指向 `GLOBAL_CLAUDE.md` 的 pointer（含 issue/BACKLOG 工作流）                                                           |

策略：增量 Edit 不重写整篇。`/start /finish /commit` 详写保留。

## 文件清单

- 改：`skills/finish/SKILL.md`
- 改：`README.md`
- 已写：`docs/13-finish收尾同步README/PROMPT.md`
- 已写：`docs/13-finish收尾同步README/PLAN.md`（本文件）

## 验证

无可执行代码，不适用单测。

- SKILL.md：本轮就是 dogfood —— 本轮属「面向用户的工作流改动」（命中触发条件 4），跑 `/finish` 时新加的 Step 3.5 应自检触发并复盘 README 是否还需再改一轮（理论上本轮已基线补齐，不应再变）
- README 基线：commit diff 人工 review，重点核对 (a) skill 列表与 `ls skills/` 一致 (b) hooks/templates 段路径都存在

## 局限性 / 后续 TODO

- 跨多轮累计的小漂移仍漏：每轮单独看都不触发，合起来 README 仍会慢慢落后 —— 接受，可作为后续 issue（定期跑「README 全量 review」）
- 「面向用户的工作流改动」边界依赖 AI 判断 —— 接受，方向 B 已比 A 收敛了大头
- 多语言：当前 README 中文，未来若加英文版需扩展 review 范围
