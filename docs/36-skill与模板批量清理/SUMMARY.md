# Round 36 开发总结 — skill 与模板批量清理

## 开发项背景

本轮批量处理 4 条积压 issue，定位「清理文档 / skill / 模板类型的修改」：

- **#13**（feat/skill）：`/finish` 收尾默认「rebase → FF merge → 删 worktree → 删分支 → 删 backup tag」一站到底，但发包/外审前留分支、继续迭代、高风险轮多保 backup tag 等合理变体每次都要用户手工说明，未规约化、易遗忘。
- **#20**（feat/template）：`teleop-operator` 实战出的 uv workspace 多包单仓布局是手搓 ad-hoc 的，不归属任何 stack，`/sync-project-config` 接不住，值得沉淀成可复用模板。
- **#23**（feat/template）：原规划「ros2-python 先落、ros2-cpp 下一轮补」——但 round 33 已用合一 stack 完整覆盖。
- **#35**（bug/skill·P1）：`/start` Step 1 算轮次号只扫本树 `docs/`，并行多 worktree 各算出同一个 N+1，合入时要手动纠正目录名/分支名/轮次号。并行多 round 是核心工作流，高频复现。

## 实现方案

### 关键设计

1. **#35 编号去重用三信号源并集（方案 C）**：本树 `docs/N-*` ∪ `git branch --list 'round*'` 解析 `round<N>-*` ∪ `git worktree list` 各 worktree 的 `docs/N-*`，取 max+1，解析失败跳过不报错。分支名信号最鲁棒（worktree 一创建即带 N，docs 还没建也防撞）。

2. **#20 走完整 A（新建 stack）而非 escape-hatch 文档**：用户决策。虚拟根的核心难点是**它没有 `[project]`，绝不能 `uv init --package`**（否则写出 `[project]`+`src/` 破坏 workspace 形态）。解法：虚拟根 `pyproject.toml` 完全由 workspace fragments 合并而成（fragment 合并对「目标不存在」走创建路径），dev 依赖复用既有 `uv add --dev`（实测在虚拟根能正确写 `[dependency-groups] dev` 并触发 sync）。这要求改 `bootstrap` Step 3.3.6/3.5 与 `sync-project-config` 2.4/4.4 各加 workspace 分支——比「简单修改」重，但模板才真正可被两个 skill 消费。

3. **fragment 命名约定的边界**：`pyproject.toml.<section>.fragment` 的 `<section>` 按 `-` 映射到 `[tool.*]` 层级（`uv-workspace`→`[tool.uv.workspace]` 成立）。但 PEP 735 的 `[dependency-groups]` 是顶层段、不在 `[tool.*]` 下，硬塞进该命名体系会歧义——故**不**为 dev group 做 fragment，改用 `uv add --dev` 在虚拟根写入。

4. **#23 判定为已完成**：round 33 的 `templates/ros2/` 单一 stack 已同时含 `ros2_py_pkg` + `ros2_cpp_pkg`、`rules/ros2.md` 已落，issue 范围被完整覆盖（合一更对——一仓即一 colcon 工作空间，拆两 stack 会在 `__root__` 撞车）。无代码，`Closes #23` 备注取代关系。

### 开发内容概括

- `skills/start/SKILL.md`：Step 1 编号识别扩为三信号源并集 + WHY 注释。
- `skills/finish/SKILL.md`：ARGUMENTS 解析 `--no-merge`(同义 `--keep-branch`)/`--keep-backup`/`--no-rebase`；Step 8 顶部「默认 vs 各选项」对比表；8.2/8.3/8.4 分支化 + 新增 `8.4-skip`。
- `templates/python-uv-workspace/`：`stack.yml` + 6 个根级 fragment（`uv-workspace`/`uv`/`uv-index`/`ruff`/`pytest`/`.vscode`）+ `packages/` 下 `example_core`(库) + `example_app`(应用，跨成员依赖) + `packages/README.md`。
- `skills/bootstrap/SKILL.md` + `skills/sync-project-config/SKILL.md`：触发条件放宽含 workspace，workspace 分支跳过 `uv init`、fragment 创建虚拟根、`uv add --dev` 写 dev group。
- `rules/python.md` §2.2「多包 uv workspace escape hatch」；项目 `CLAUDE.md`、`README.md` 同步。

### 额外产物

- 参考成员包自带 happy-path pytest（`example_core` 纯函数先写测试，符合 TDD；`example_app` 跨成员 import 冒烟）。
- `/tmp` 临时 scaffold 端到端验证：`uv sync`（两成员 build + 跨成员依赖解析）→ `uv add --dev`（虚拟根写 `[dependency-groups] dev`）→ `uv run pytest`（4 passed，importlib 模式两成员同名 `tests` 无碰撞）→ `ruff check` clean。

## 局限性

- `python-uv` 与 `python-uv-workspace` **互斥**靠 stack.yml / README 文档约定，bootstrap 多选 UI **不强制**拦截二者同选；同选会向根 pyproject 注入打架配置。
- 成员 `pyproject.toml` 的 `[build-system] requires = ["uv_build>=0.11.11,<0.13.0"]` 版本范围会随 uv 升级过时，需人工 bump（与 react-vite 写死 npm 版本同理）。
- 三个 skill 改动是指令型文档，无可执行单测，靠文档自洽 + 人工核对；只有模板成员包有真实 pytest 兜底。
- `--no-rebase` 与默认 merge 组合时仅「已可 FF」才合并，否则停下提示——这是有意的保守语义，非全自动。

## 后续 TODO

- 若实战发现 `python-uv` / `python-uv-workspace` 同选造成困扰，可在 bootstrap stack 选择处加互斥校验。
- `uv_build` 版本范围的人工 bump 可考虑做成 `/pybump` 式的小维护脚本（低优）。

## 可沉淀项

本仓库即 claude-code-global 本身（自指），跨项目资产候选按约定走**本地 `/backlog`**、不跨仓自 file。本轮的可复用经验本就是直接落进本仓的产物（新 stack + 两 skill 接入 + rules 文档），无额外需另起 issue 的沉淀项。一个值得记的模式（非新 issue，仅备忘）：

- **fragment 命名约定的隐含边界**——`pyproject.toml.<section>.fragment` 默认 `<section>`→`[tool.<section>]`，PEP 735 顶层段（`dependency-groups`）落在体系外，遇到这类顶层非-`tool` 配置应改用 skill 内的命令式写入（如 `uv add`）而非硬造 fragment。该认知已写进本轮 SUMMARY 与两个 skill 的 workspace 分支注释，无需另开 issue。
