> 来自 [#17 Python 模板默认 uv python-preference=only-managed + rules/python.md 记坑](https://github.com/pkulijing/claude-code-global/issues/17)
> Labels: `type:refactor` `area:template` `priority:P2`

# 需求：Python 模板默认 `python-preference = "only-managed"` + rules/python.md 记坑

## 背景

来源：`teleop-survey` round 10（GitLab 私有仓库），在真实采集 PC（Ubuntu）上部署 FastAPI daemon、跑 `uv sync` 时踩坑，由该项目 `/finish` 跨项目自动沉淀为本仓库 issue #17（未进任何 BACKLOG 索引）。

## 现象 / 根因

`uv sync` 编译 `evdev`（C 扩展）失败：`command '/usr/bin/x86_64-linux-gnu-gcc' failed`，根因是缺 `Python.h`。诊断发现 venv 的 `base_prefix` 指向 `/usr` —— **uv 复用了系统 python，而不是下载托管版**：

- `python-downloads`（默认 `automatic`）**只在找不到任何满足版本要求的解释器时**才下载托管 python；
- `python-preference`（默认 `managed`）只是在**已安装**的解释器间排序，并不强制下载。

该机器系统已有 `python3.12`（满足要求）→ uv 直接复用它；而系统 python 没装 `python3-dev` → `/usr/include/python3.12` 无 `Python.h` → C 扩展编译失败。`apt install python3-dev` 又违背「让 uv 全权管 python」的意图。

## 为什么值得沉淀

任何**含 C 扩展依赖**、在「系统 python 未装 dev 包」的机器上跑 uv 的项目都会撞这个坑，复发率高、排查耗时（容易误以为是 gcc/编译器问题）。uv 托管的 standalone python 永远自带头文件，设 `only-managed` 一劳永逸：uv 忽略系统 python，配合默认 `python-downloads = automatic`，没有满足要求的托管 python 时会自动下载一份自带头文件的 standalone python。

## 建议落点（issue 原文）

1. claude-code-global 的 **Python 项目模板（pyproject）默认加**：

   ```toml
   [tool.uv]
   python-preference = "only-managed"
   ```

2. **`rules/python.md` 增一条**：uv 默认可能复用系统 python；含 C 扩展、或希望 uv 全权管 python 时设 `only-managed`，避免系统 python 缺 `Python.h` 致编译失败。
3. （可选）`install.sh` 写 `~/.config/uv/uv.toml`，设系统级 `only-managed` + 清华源默认。

## 本轮范围

- **核心（必做）**：落点 1 + 落点 2。
  - 落点 1 落到 python-uv 模板的 fragment 机制：新增 `templates/python-uv/__subpath__/pyproject.toml.uv.fragment`，承载 `[tool.uv] python-preference = "only-managed"`。bootstrap / sync-project-config 的 fragment 合并逻辑对 `pyproject.toml.*.fragment` 是通用的，新片段会被自动拾取。
  - 落点 2 落到 `rules/python.md` §1（环境与工具），新增一条说明。
- **可选（落点 3）**：是否同时把系统级 `~/.config/uv/uv.toml` 纳入 `install.sh` 管理，待 PLAN 阶段与用户确认。系统级配置作用域更大、且与现有「per-project fragment」的设计哲学不同，倾向单独成轮或本轮明确取舍。
