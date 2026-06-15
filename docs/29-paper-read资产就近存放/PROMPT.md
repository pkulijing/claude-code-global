# PROMPT

> 来自 [#15 paper-read: 资产应与笔记 markdown 同级，而非机械地放根目录 assets](https://github.com/pkulijing/claude-code-global/issues/15)
> Labels: `type:bug` `area:skill` `priority:P2`

## 背景

`paper-read` skill 的 `SKILL.md` 在「文件格式 - 格式要求」一节硬性规定：

> 论文内容中的重要插图、复杂的函数图像直接在 markdown 中插入，图片文件保存到**根目录下的** assets 文件夹。

这条规则把资产位置写死在「仓库根目录的 assets」。

## 问题

在按目录组织的笔记仓库里，这个默认是错的。典型场景（paper-reading 仓库）：按领域分文件夹、每篇论文独占一个子文件夹，资产应当**跟笔记本体（markdown 文件）同级**：

```
1-algorithm/
  1-act/
    reading1.1-aloha-act.md
    assets/                  # 与笔记同级，就近存放
      act-algo-1.png
```

机械地要求「保存到根目录 assets」会带来几个问题：

- **就近性丢失**：图片离引用它的笔记很远，阅读/维护时来回跳。
- **可移植性差**：一篇论文的笔记 + 图片无法作为一个自包含文件夹整体迁移/删除，根 assets 会沉淀跨论文的孤儿图片。
- **命名冲突**：多篇论文的图片挤在同一个根 assets 下，得靠前缀人为去重。

目前只能靠项目级 `CLAUDE.md` 覆盖这条默认（skill 里也确实写了「若项目级 CLAUDE.md 另有规则以项目为准」），但这是把一个本该合理的默认推给每个项目兜底。

## 期望

把默认行为改成「资产与笔记 markdown 文件同级的 `assets/` 目录」，即**就近原则**，而不是固定根目录：

- 笔记落在哪个目录，`assets/` 就建在同目录下，引用用相对路径 `![](assets/xxx.png)`。
- 这样无论是单文件笔记（assets 在笔记旁）还是结构化多层仓库（assets 在论文文件夹内），默认都成立。

涉及改动：`skills/paper-read/SKILL.md` 中「图片文件保存到根目录下的 assets 文件夹」一句的措辞。
