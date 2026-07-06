# README review & update（finish Step 6 展开）

放在 commit 之前，让 README 改动跟本轮代码进同一 commit。仅当本轮变更命中触发清单才执行；否则打印一行「README review skipped: 本轮变更不在触发清单」并跳过。

## 触发条件清单（满足任一即触发）

1. **skill 增减**：`skills/<name>/` 子目录新增或删除。
2. **hook 增减**：`hooks/*` 文件新增或删除。
3. **顶层目录结构变化**：仓库根、`skills/` / `templates/` / `hooks/` 这几层出现新增 / 删除子目录。
4. **面向用户的工作流改动**：本轮 PROMPT.md / SUMMARY.md 明示「面向用户的入口 / 约定改了」（需求管理、安装方式、模板使用方式、命令行接口等）。

**明示不触发**：纯内部重构（重命名 / 抽函数 / 调分割）、bug fix、仅改 `docs/` 开发记录、依赖升级。

## 判定数据源

- `git status --porcelain` + `git diff --cached --name-status` 的并集（本步在 commit 前跑，未提交变更也算）。
- **明示忽略**前面几步刚改的 `SUMMARY.md` / `DEVTREE.md` 自身——它们不应触发 README review。

## 触发后子步

1. 读 `README.md` + 本轮 `PROMPT.md` / `SUMMARY.md`。
2. 列出 README 中需新增 / 修改的具体段落（**只动相关段落，不重写整篇**）。
3. 直接 Edit `README.md`。
4. 一句话告知用户改了什么（例：「README 已更新：在 Skills 段新增 `/foo` 一节」）。
