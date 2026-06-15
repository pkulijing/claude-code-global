# 需求：编辑器配置（`.vscode/`）落项目根、跨 stack 合并

## 背景

round 30 沉淀了 `react-vite` 前端栈模板，把整套前端脚手架（含 `.vscode/extensions.json` + `.vscode/settings.json`）放在 `templates/react-vite/__subpath__/` 下，落点由 `stack.yml` 的 `default_path: frontend` 决定——即前端的 `.vscode/` 最终落在项目的 `frontend/.vscode/` 子目录。

## 现象 / 问题

用户实际使用时发现：**打开项目根目录，VS Code 不会提示安装 `frontend/.vscode/extensions.json` 里推荐的插件（biome）**。

根因：VS Code 在单根工作区下**只读取「工作区根目录」的 `.vscode/`**，子目录（如 `frontend/.vscode/`）的 `extensions.json` 推荐与 `settings.json` 配置在「打开仓库根」这一惯常用法下完全不生效。而本仓库的开发惯例就是「打开项目根」，于是前端栈的编辑器增益形同虚设。

对照后端 `python-uv` 栈：它的 `default_path` 是 `.`（落根），所以它的 `__subpath__/.vscode/` 恰好落在根目录、能正常生效——但这只是「落点恰好是根」的巧合，不是一个对「子目录 stack」也成立的统一机制。

## 期望

把编辑器工作区配置（`.vscode/extensions.json` + `.vscode/settings.json`）作为**项目根级、且可跨 stack 合并**的资源来管理，使得：

1. 无论 stack 落点是根（`python-uv`）还是子目录（`react-vite`），其编辑器推荐 / 设置都汇聚到**项目根的 `.vscode/`**，打开根目录即生效。
2. 前后端并存的混合仓库里，两个 stack 的推荐（ruff + biome）与 settings（`[python]` / `[typescript]` …）能**合并共存**，而不是相互覆盖、只剩一个 stack 的配置。
3. 合并后的根级 `settings.json` **不污染其他语言**：前端 Biome 不能成为 Python 文件的默认格式化器。

## 约束 / 关注点

- 复用仓库既有的 **fragment 合并机制**（`pyproject.toml.*.fragment` 已是先例）作为参照，保持机制一致、可被 `bootstrap` / `sync-project-config` 两端消费。
- react-vite 当前的 `settings.json` 含**全局键**（`editor.defaultFormatter` / `editor.formatOnSave` / 全局 `codeActionsOnSave`），落根会波及 Python；需改为**全语言作用域**（对照 python-uv 的写法）。
- 需要兼顾**存量项目迁移**：已 bootstrap 出 `frontend/.vscode/` 的项目，下次 `sync` 时应能平滑过渡。
- 文档与机制说明（SCHEMA / 规则 / CLAUDE.md / 相关 docs）同步更新到「当前真相」。
