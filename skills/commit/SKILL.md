---
name: commit
description: 按照 git 规则自动分析变更并提交代码
disable-model-invocation: true
---

用户调用此 skill 表示要提交当前的代码变更。按照全局 CLAUDE.md 中的 git 规则执行以下步骤：

1. 运行 `git status` 查看当前变更状态
2. 运行 `git diff` 查看具体变更内容（包括已暂存和未暂存的）
3. 运行 `git log --oneline -5` 了解近期 commit 风格
4. 分析所有变更，生成 commit message：
   - 使用中文
   - 遵循 semantic commit message 规则（如 `feat:`, `fix:`, `refactor:` 等）
   - 简明扼要，聚焦于「为什么」而非「改了什么」
5. 将相关文件添加到暂存区（优先按文件名添加，避免 `git add -A`）
6. 执行提交，commit message 末尾必须包含：
   ```
   Co-authored-by: Claude <noreply@anthropic.com>
   ```
7. 运行 `git status` 确认提交成功
