> 来自 [#10 [Spike] 为仓库引入用户可配置项机制（首例：git init 默认分支）](https://github.com/pkulijing/claude-code-global/issues/10)
> Labels: `type:refactor` `area:install` `priority:P1`

## 背景

当前仓库把所有行为/偏好都**硬编码**在三处：`GLOBAL_AGENTS.md`（开发规范）、`install.sh`（安装流程）、各 `skills/`。没有任何「用户可配置项」机制。

直接触发点：希望 `git init` 的默认分支是 `master`，但也有人更偏好 `main` —— 这本质是**个人偏好**，不该硬编码进面向所有用户的全局配置。

本 issue 是一个 **Spike（调研为主）**：验证仓库是否值得、以及如何引入一层「用户可配置机制」，并为「git init 默认分支」做最小 PoC。

## 验证目标

能回答出以下问题，并产出一个最小可行设计：

1. **配置放哪**：`~/.claude/` 下一个用户配置文件？还是 install.sh 交互式询问？
2. **配置项如何被各消费方读取**：install.sh / skill / hook 三类消费方分别怎么拿到配置值？
3. **多设备自动同步时如何不被覆盖**：`auto-update.sh` 会 pull + install，用户的本地配置必须不被同步流程覆盖。

## 方法

- 调研现有 `install.sh` 的 settings 合并机制（`settings.base.json` 合并、`codex.config.base.toml` marker 块合并）能否复用为配置读取/合并的基础。
- 盘点当前所有「硬编码偏好」候选项（git init 默认分支、commit trailer 署名模型 等），判断哪些值得提取为可配置项。
- 为「git init 默认分支」做最小 PoC：配置项 → install.sh 读取 → `git config --global init.defaultBranch <值>`。

## 预期产出

- 一份**设计文档**：配置文件位置 + schema + 读取方（各消费方约定）+ 与多设备同步的关系。
- 「默认分支」首例的**可落地方案**（PoC 或正式实现，视调研结论而定）。

## scope

- 以**调研**为主，时长上限约半天。
- 超时就把已有结论写进 issue 并拆分后续 feat。
- 本 spike 结论将派生后续 feat（含「git init 默认分支可配置」）。
