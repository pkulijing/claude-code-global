---
name: finish
description: 完成当前开发项：撰写 SUMMARY.md 总结文档并提交代码
disable-model-invocation: true
---

用户调用此 skill 表示当前开发项已完成。

**参数处理**：调用时可能附带参数（args），参数是用户对本次开发的额外说明，比如需要特别强调的点、遗留问题、后续 TODO 等。撰写 SUMMARY.md 时应把参数内容融入到对应章节中（如「局限性」「后续TODO」或「关键设计」）。若无参数则按常规总结即可。

执行以下步骤：

1. 按照全局 CLAUDE.md 中「总结」部分的要求，在 `docs/` 下当前开发项文件夹中撰写 `SUMMARY.md`（结合参数内容）
2. 使用 `/commit` 提交所有变更（包括 SUMMARY.md）
