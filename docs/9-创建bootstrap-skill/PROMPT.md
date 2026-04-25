# 需求：新增 /bootstrap skill 处理空项目初始化

## 背景

现有 `/start` skill 假设项目已有基础文档骨架（`CLAUDE.md` / `BACKLOG.md` / `DEVTREE.md` / `README.md`），直接进入「开新一轮开发项」的流程。但当一个全新空项目要启动第一轮开发时，这些骨架都还不存在，单跑 `/start` 会缺东西。

## 设计取舍

两条路：

1. **改 `/start`**：让它检测空项目并自动建骨架
2. **新增 `/bootstrap`**：把空项目脚手架职责单拎出来

选择 **方案 2**，理由：

- `/start` 是热路径（每轮都跑），bootstrap 整个项目只跑一次。把一次性分支塞进高频 skill 会让每次 `/start` 都载入不会触发的逻辑，违反单一职责。
- 两件事的本质不同：`/start` 是循环工作流入口（开一轮开发），bootstrap 是一次性脚手架（立项目骨架）。
- 解耦后 bootstrap 未来可以扩展（`git init`、`.gitignore` 模板、`.env.example` 等）而不污染 `/start`。

代价是用户多记一个命令，且首次容易忘记。通过让 `/start` 在检测到空项目时主动提示「请先运行 /bootstrap」来补偿。

## 目标

1. 新增 `skills/bootstrap/SKILL.md`，负责为空项目搭建：`README.md` + `CLAUDE.md` 两个文件，并通过调用 `/devtree` 让其落 `DEVTREE.md` 骨架
2. 修改 `skills/devtree/SKILL.md`，让其在「文件不存在 / Epic 结构为空」时落初始骨架而非报错
3. 修改 `skills/start/SKILL.md`，增加前置检查：若项目未初始化，停下来提示运行 `/bootstrap`
4. 重新运行 `install.sh` 让新 skill 生效

## 非目标

- 不创建 `BACKLOG.md`：让 `/backlog` 自己处理首次创建（它本身就有「文件不存在时初始化」分支），bootstrap 不重复一份骨架模板，避免双向同步
- 不调用内置 `/init`：`/init` 依赖代码扫描，对空项目意义不大，等代码长起来再让用户手动跑
- 不调用 `/commit`：是否立即提交由用户决定（与 `/backlog` 一致）

## 关键设计原则：单一事实来源

- DEVTREE.md 骨架的唯一定义在 `/devtree` skill 内，bootstrap 不重复一份模板（避免双向同步漂移）
- 等价地，`/devtree` 自身要兼容「冷启动」状态
