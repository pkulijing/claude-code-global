---
name: bootstrap
description: 为空项目搭建文档骨架（README.md / CLAUDE.md / DEVTREE.md），仅在项目首次开发前调用一次
disable-model-invocation: true
---

用户调用此 skill 表示要为一个**全新空项目**搭建文档骨架。本 skill 是一次性脚手架，**不**用于已有 `docs/` 历史的项目。

## 前置检查

按顺序检查，**任一命中就立即停止并报告**，不要尝试覆盖已有内容：

- `docs/` 下已存在 `N-` 数字前缀开头的开发轮次目录 → "项目已初始化（检测到 docs/N-xxx），不应运行 bootstrap。"
- `CLAUDE.md` 已存在 → "已有 CLAUDE.md，如要重置请先备份再删除原文件。"
- `DEVTREE.md` 已存在 → 同上提示

全部通过才继续。

## 信息收集

**一次性问全**，不要逐条来回：

1. **项目名称**（默认取当前目录名，告知默认值）
2. **项目一句话描述**（用作 README 与 CLAUDE.md 的开篇）
3. **是否已有第一个待启动开发项的初步想法？**（仅用于决定收尾时是否提示运行 `/backlog`，不需要详细内容）

参数（args）若非空，可作为问题 1 或 2 的输入；不足部分仍需向用户问全。

## 执行流程

### Step 1：写 README.md

```markdown
# {项目名}

{一句话描述}

## 目录结构

（待补充）

## 开发流程

本项目遵循 [全局 Constitution](~/.claude/CLAUDE.md) 中定义的「需求 - 计划 - 执行 - 总结」四步开发模式，文档记录见 `docs/`。
```

### Step 2：写 CLAUDE.md

```markdown
# {项目名}

{一句话描述}

## 目录结构

（待补充）

## 开发注意事项

（待补充）
```

**不**调用内置 `/init`：空项目无可扫的代码，等代码长起来后由用户手动跑 `/init` 重写更合适。

### Step 3：调用 `/devtree` 落 DEVTREE.md 骨架

直接调用 `/devtree`。`/devtree` 自身已支持「冷启动」：当 `docs/DEVTREE.md` 不存在或 Epic 结构为空时，会写入完整骨架（分类图例 + 可视化占位 + 节点索引占位 + Epic 结构占位）。

**不要**在本 skill 里复制一份 DEVTREE 骨架模板 —— 单一事实来源在 `/devtree`。

### Step 4：收尾反馈

- echo-back 三个新建文件的路径：`README.md`、`CLAUDE.md`、`docs/DEVTREE.md`
- 给出下一步建议清单：
  1. 检查并补完 `README.md` 与 `CLAUDE.md` 的「待补充」段
  2. 在 `DEVTREE.md` 的「Epic 结构」区块下添加首批叶 Epic
  3. 若已有第一个开发项想法（信息收集第 3 问回答「有」），运行 `/backlog` 登记
  4. 准备好后运行 `/start` 开启 round 0
- **不调用 `/commit`** —— 是否立即提交由用户决定（与 `/backlog` 一致）
