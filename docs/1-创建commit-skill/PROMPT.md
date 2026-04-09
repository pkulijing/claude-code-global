# 需求：创建 commit skill

## 背景

`finish` skill 中引用了 `/commit`，但该 skill 尚未创建。需要在 `skills/` 下新建 `commit` skill。

## 需求

创建一个 `commit` skill，功能为：按照全局 CLAUDE.md 中的 git 规则，自动完成代码提交。包括：
- 查看当前变更状态
- 分析变更内容，生成符合 semantic commit message 规则的中文 commit message
- 末尾包含 `Co-authored-by` trailer
- 执行提交
