# SUMMARY：Python 模板默认 `python-preference = "only-managed"` + rules 记坑 + 系统级 uv.toml

> 关联 issue [#17](https://github.com/pkulijing/claude-code-global/issues/17) · round 31

## 开发项背景

`teleop-survey`（私有 GitLab）在 Ubuntu 采集机上 `uv sync` 编译 `evdev`（C 扩展）失败，由该项目 `/finish` 跨项目沉淀为本仓库 issue #17。

希望解决的问题：让本仓库管理的 Python 工程链路**默认规避「uv 复用系统 python 致 C 扩展编译失败」这一高复发坑**，无需开发者每次手动想起。

## 实现方案

### 关键设计

1. **根因 → 一行配置**：uv 默认 `python-preference=managed` 只在已装解释器间排序、会优先复用满足版本的系统 python；系统 python 常缺 dev 头文件（无 `Python.h`）→ C 扩展编译失败。设 `python-preference = "only-managed"` 让 uv 忽略系统 python；配合默认 `python-downloads=automatic`，缺托管版时自动下载自带头文件的 standalone python。**只设这一个键即可**，无需显式 `python-downloads`。

2. **落点 1 复用现成 fragment 机制**：python-uv 模板的 `pyproject.toml` 由 `pyproject.toml.<section>.fragment` 拼装，bootstrap / sync 的合并对 `pyproject.toml.*.fragment` 是**通用 glob**，新增 `pyproject.toml.uv.fragment`（`uv`→`[tool.uv]`）即被自动拾取，**零代码改动**。它与已有 `uv-index` 片段同属 `tool.uv` 命名空间但落不同 key，合并互不冲突。

3. **落点 3 选 user-wins seed 而非 TOML merge**：`~/.config/uv/uv.toml` 的 `python-preference` 是**标量键**，沿用 codex 那套 marker-block 追加策略会在用户已设同键时触发 TOML 重复键错误。故采用与 `ccg_seed_user_config` 一致的「缺省才填、绝不覆盖」语义：文件不存在才创建，已存在一律不碰并打印手动提示。代价是已有 uv.toml 的机器不被自动改写（见局限性）。

4. **uv.toml vs pyproject 的 key 形态差异**：`~/.config/uv/uv.toml` 直接用顶层 `python-preference` + `[[index]]`（不带 `tool.uv` 前缀），与 pyproject 里的 `[tool.uv]` / `[[tool.uv.index]]` 不同——base 文件与注释都显式标注了这一点，避免后续误抄。

### 开发内容概括

- **新建** `templates/python-uv/__subpath__/pyproject.toml.uv.fragment`：`[tool.uv] python-preference = "only-managed"`（落点 1）。
- **新建** `uv.config.base.toml`（repo 根）：推荐的系统级 uv 配置基线（only-managed + 清华源默认 index）（落点 3）。
- **改** `install.sh`：新增 `seed_uv_config` 函数（user-wins seed，挂在 `merge_toml` 后）+ 在「用户可配置项」块之后、调度器之前新增机器级全局调用段（落点 3）。
- **改** `rules/python.md` §1：新增一条 bullet 说明该坑与对策（落点 2，措辞遵循 §3.4 不绑 issue/round）。
- **改** `skills/bootstrap/SKILL.md` / `skills/sync-project-config/SKILL.md`：section 命名示例补 `uv → [tool.uv]`，覆盖本轮新增片段类型。
- **改** `CLAUDE.md`：目录结构段补 `uv.config.base.toml` 条目 + install.sh 职责补「系统级 uv 配置 seed」+ 开发注意事项补「改 base 后需重装、user-wins 不覆盖」。

### 额外产物

- 验证脚本（一次性，未落库）：用 `python3.12` 的 `tomllib` 校验两份 TOML 的语法与 key 落点；用 awk 抽取 install.sh 里**真实**的 `seed_uv_config` 函数体，在隔离的临时 `XDG_CONFIG_HOME` 下跑 4 个分支（创建 / 已存在 user-wins ×2 / 基线缺失）全绿；`bash -n install.sh` 语法检查通过。

## 局限性

- **已有 `~/.config/uv/uv.toml` 的机器不被自动改写**：user-wins seed 只对该文件缺失的机器生效。已有该文件（哪怕没设 `python-preference`）的机器只会看到 install 的一行手动提示，需用户自行加键。这是「绝不覆盖用户配置」与「机器级一劳永逸」之间的取舍，本轮选了前者。
- **真机 install 未在本轮跑**：从 worktree 跑 `install.sh` 会把 `REPO_DIR` 指向临时 worktree、连带把 `~/.claude` 软链重指到 worktree，故真机安装刻意推迟到 `/finish` 合并回主干后再跑——届时 `seed_uv_config` 才会对本机真实 `~/.config/uv/uv.toml` 生效。

## 后续 TODO

- （可选 follow-up）若要让「机器级 only-managed」对已有 uv.toml 的机器也生效，需实现真正的**幂等 TOML 字段 merge**（仅当未设 `python-preference` 时补该键，保留其余内容）。当前 bash 无 TOML 写库，稳妥做法是引一个轻量 TOML 编辑器（如 `taplo` 或 uv 托管 python + `tomlkit`），单列一轮评估。
- 多设备 auto-update 每小时跑 install，合并后所有联网设备会在下次同步时自动 seed（仅缺文件的设备）——可观察一两台设备确认行为符合预期。

## 可沉淀项

- **`/start` 轮次编号未计入「在途但未提交 docs」的并行轮**：本轮 `/start 17` 按「扫 `docs/` 取 max+1」算出 29，但并行的 round29 / round30 worktree 已开、各自 docs 还没提交，导致撞号、事后手工把本轮改成 31。
  - 落点：`/start` skill 计算 N 时，除扫 `docs/<N>-*` 目录外，也并入 `git worktree list` 与 `round<N>-*` 分支名里的编号，取三者并集的 max+1。并行 worktree 开发常态化后这是高频摩擦。
  - 去向：**当前仓库即 claude-code-global（自指守卫触发）** → 不跨仓 file，建议在本仓跑 `/backlog` 起本地 issue 走 BACKLOG 索引。
