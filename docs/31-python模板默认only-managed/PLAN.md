# PLAN：Python 模板默认 `python-preference = "only-managed"` + rules 记坑 + 系统级 uv.toml

> 关联 issue [#17](https://github.com/pkulijing/claude-code-global/issues/17) · round 31 · worktree `round31-python模板默认only-managed`

## Context（为什么做这件事）

`teleop-survey` 在 Ubuntu 采集机上 `uv sync` 编译 `evdev`（C 扩展）失败，根因不是编译器，而是 **uv 默认复用了系统 python**：系统已有满足版本的 `python3.12`（`python-preference=managed` 只在已装解释器间排序、不强制下载），但系统 python 没装 `python3-dev` → 无 `Python.h` → C 扩展编译失败。

任何「含 C 扩展依赖 + 系统 python 未装 dev 包」的机器都会复发此坑，排查耗时且易误判为编译器问题。uv 托管的 standalone python 永远自带头文件，设 `python-preference = "only-managed"` 让 uv 忽略系统 python、必要时自动下载托管版，一劳永逸。

本轮把这条经验固化为三处落点（用户已确认含系统级 uv.toml）：模板默认带上、规则文档记一条坑、`install.sh` seed 系统级默认。

## 落点 1：python-uv 模板新增 `[tool.uv]` fragment

python-uv 模板的 `pyproject.toml` 由 `pyproject.toml.<section>.fragment` 片段拼装，bootstrap / sync-project-config 对 `pyproject.toml.*.fragment` 做**通用**智能合并（见 `skills/bootstrap/SKILL.md:123-128`、`skills/sync-project-config/SKILL.md:133-141`）。命名约定：`<section>` 以 `-` 分层并隐含 `tool.` 前缀（`ruff`→`[tool.ruff]`、`uv-index`→`[[tool.uv.index]]`）。

**新建** `templates/python-uv/__subpath__/pyproject.toml.uv.fragment`（`uv`→`[tool.uv]`，与已有 `uv-index` 片段同属 `tool.uv` 命名空间但落不同 key，合并互不冲突）：

```toml
[tool.uv]
python-preference = "only-managed"
```

> 只设 `python-preference`，不设 `python-downloads`——默认 `automatic` 配合 `only-managed` 已能在缺托管版时自动下载，无需显式声明。

**无需改** bootstrap / sync 的合并代码：fragment glob 是通用的，新片段自动被拾取。

## 落点 2：`rules/python.md` §1 增一条

在 §1「环境与工具」追加一条 bullet（遵循 §3.4：写「why / 当前真相」，不绑定 issue 号 / round），说明：uv 默认（`python-preference=managed`）可能复用系统 python；含 C 扩展或希望 uv 全权管 python 时，在 `pyproject.toml` 设 `[tool.uv] python-preference = "only-managed"`，避免系统 python 缺 `Python.h` 致编译失败；python-uv 模板已默认带、手工建项目照抄；机器级一劳永逸可在 `~/.config/uv/uv.toml` 设同名键（`install.sh` 缺失时自动 seed）。

## 落点 3：`install.sh` seed 系统级 `~/.config/uv/uv.toml`

**策略：user-wins seed（缺省才填、绝不覆盖）**，与本仓库既有的用户可配置项 seed 哲学（`scripts/user-config.sh` 的 `ccg_seed_user_config`）一致，也规避「bash 里安全 merge TOML 标量键」的雷（系统已有 `python-preference` 时 marker-block 追加会触发 TOML 重复键错误）。

- **新建** repo 根 `uv.config.base.toml`（committed，与 `settings.base.json` / `codex.config.base.toml` 并列的 base 文件），内容即推荐的系统级 uv 配置（顶层 `python-preference = "only-managed"` + `[[index]]` 清华源默认）。

  > 注意 `uv.toml` 的 key 不带 `tool.uv` 前缀（顶层 `python-preference` + `[[index]]`），与 pyproject 里的 `[tool.uv]` / `[[tool.uv.index]]` 写法不同。

- **新增** `install.sh` 函数 `seed_uv_config <base> <dst>`：
  - 解析目标路径 `${XDG_CONFIG_HOME:-$HOME/.config}/uv/uv.toml`；
  - dst 不存在 → `mkdir -p` 父目录 + `cp` base → `success`；
  - dst 已存在 → 不动，`info` 一行「已存在，用户自管」并提示可手动加 `python-preference = "only-managed"`（幂等、auto-update 每小时跑不刷屏）。
- **挂载点**：在 install.sh「用户可配置项」块之后、调度器之前新增一个机器级全局段（与具体 agent 端无关，故不放进 `deploy_agent` 循环）。

## 不在本轮范围

- 不对已存在的 `~/.config/uv/uv.toml` 做字段级 merge（user-wins 只 seed 缺失文件）。已有该文件的机器不会被自动改写——靠落点 2 的文档 + install 的 info 提示用户手动加。若日后要真正的幂等字段 merge，单列 follow-up。

## 关键文件

- 新建：`templates/python-uv/__subpath__/pyproject.toml.uv.fragment`
- 新建：`uv.config.base.toml`（repo 根）
- 改：`install.sh`（加 `seed_uv_config` 函数 + 全局调用段）
- 改：`rules/python.md`（§1 加一条 bullet）
- 改（可选小修）：`skills/bootstrap/SKILL.md` / `skills/sync-project-config/SKILL.md` 的 section 命名示例补 `uv → [tool.uv]`
- 文档：`docs/31-python模板默认only-managed/{PROMPT,PLAN,SUMMARY}.md`
- 收尾：`CLAUDE.md` 目录结构段补一行 `uv.config.base.toml` 说明

## 验证

1. **fragment TOML 合法**：解析 `pyproject.toml.uv.fragment` 与 `uv.config.base.toml`，确认无语法错误、key 落点正确。
2. **`seed_uv_config` 幂等性**（用临时 HOME，不碰真实 `~/.config`）：空目录→创建；再跑→不变；预置自定义→保留。
3. **install.sh 不回归**：`bash -n install.sh` 语法检查 + 真机重跑。
4. （文档落点）人工核对 `rules/python.md` 新 bullet 符合 §3.4（无 issue 号 / round 引用）。
