# PROMPT — 接入 prettier/ruff format-after-edit hook（全局化）

## 起源

daobidao 项目在 commit `c8c91c7` 接入了一个 PostToolUse hook：CC 编辑 `.py` / `.md` 后自动调 `ruff format` / `prettier --write`，目的是消除 **「CC 编辑文件 → 用户在 VS Code 保存触发 formatOnSave → 整文件大 diff」** 的反复重排。

这个痛点在所有项目都存在，不止 daobidao。希望把 hook 提到全局，所有项目共享一份。

## 目标

把 daobidao `c8c91c7` 中**可全局化的部分**搬到 `claude-code-global` 仓库：

- ✅ `format-after-edit.sh` 脚本本体
- ✅ `settings.base.json` 中的 PostToolUse hook 配置
- ✅ `install.sh` 部署逻辑（软链脚本到 `~/.claude/hooks/`）

**不**搬的部分：

- ❌ `.prettierrc` —— prettier 从 cwd 往上找配置，全局没法覆盖；改为在 `GLOBAL_CLAUDE.md` 里加一条「项目本地推荐配置」约定
- ❌ `.vscode/settings.json` 和 `.vscode/extensions.json` —— 是 IDE per-project 配置，不属于 CC 全局仓库职责，由各项目自行维护

## 范围外

- 不改 daobidao 仓库（用户自行删除项目本地的 `.claude/format-after-edit.sh` 和 `settings.json` 中的 hook 段）
- 不改 hook 的实现细节（best-effort、缺工具静默跳过的设计已经验证过，1:1 移植即可，仅做必要的路径改造）
