# PLAN

## 目标

把 `paper-read` skill 中「图片资产固定存到仓库根目录 assets」的默认，改为「资产与笔记 markdown 文件同级的 `assets/`」就近原则。

## 现状定位

[skills/paper-read/SKILL.md:27](skills/paper-read/SKILL.md#L27)（「文件格式 → 格式要求」一节）：

> 论文内容中的重要插图、复杂的函数图像直接在markdown中插入，图片文件保存到根目录下的assets文件夹。

「根目录下的 assets」是唯一需要改的措辞。skill 内已有「若项目级 CLAUDE.md 另有规则以项目为准」的兜底（在「文件命名」节），但那只覆盖命名，资产位置这条仍把不合理默认推给项目兜底。

## 改动方案

单文件、单行措辞改写，不涉及代码逻辑：

将第 27 行改为：

> 论文内容中的重要插图、复杂的函数图像直接在 markdown 中插入；图片文件保存到与笔记 markdown 同级的 `assets/` 文件夹（就近原则，而非固定根目录），引用使用相对路径 `![](assets/xxx.png)`。

要点：

- **就近原则**：笔记落在哪个目录，`assets/` 就建在同目录下。这样单文件笔记（assets 在笔记旁）与多层结构化仓库（assets 在论文文件夹内）两种形态默认都成立。
- **相对路径引用**：显式写出 `![](assets/xxx.png)`，避免再出现「根目录绝对位置」的歧义。

## 测试

本轮改动是 skill 的 markdown 文档措辞，无可执行代码、无输入输出契约，不适用 TDD。验证方式：人工通读改后句子，确认语义为「就近 assets + 相对路径引用」，且与「文件命名」节的项目级兜底措辞风格一致。

## 影响面

- 仅 `skills/paper-read/SKILL.md` 一处。
- skill 目录是目录级软链到 `~/.claude/skills/` 与 `~/.codex/skills/`，改内容即时生效，**无需** `install.sh`。
- 不触及其他 skill / 模板 / 规则文档。

## 收尾

`/finish`：写 SUMMARY.md，commit 带 `Closes #15`，rebase 回 master FF 合并并清理 worktree。
