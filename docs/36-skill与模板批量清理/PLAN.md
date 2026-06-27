# Round 36 实现计划

四项独立改动，互不耦合，可按 #35 → #13 → #20 → #23 顺序落（先轻后重，#23 仅收尾关闭）。

---

## #35 — `/start` round 编号跨 worktree 去重（最轻，纯 skill 文档）

**改动**：`skills/start/SKILL.md` 通用流程第 1 步（第 28 行）。

把「扫 `docs/` 取最大值 +1」扩成三信号源取并集（方案 C）：

1. 当前工作树 `docs/<N>-*` 目录名解析出的 N；
2. `git branch --list 'round*'`（含其它 worktree 的分支）解析 `round<N>-*` 前缀的 N；
3. `git worktree list --porcelain` 遍历每个 worktree，扫其 `docs/<N>-*` 解析 N。

三源并集取 max + 1。**解析失败（非 `round<N>-` 规范分支、自由描述分支、worktree 路径不可达）一律跳过该条、不报错**。文档里给一段示例命令 + 一句「为何要并集」的 WHY 注释。

**验证**：本轮自身就是 dogfood——当前已能正确算出 N=36（无并行在途轮）。改后再人工核对描述自洽即可（指令型 skill 无可执行单测）。

---

## #13 — `/finish` 收尾选项（skill 文档）

**改动**：`skills/finish/SKILL.md` 两处。

### 1. ARGUMENTS 处理段（第 9 行附近）

新增：解析并剔除以下开关后，再把剩余 args 当作用户对本轮的说明：

- `--no-merge`（同义词 `--keep-branch`）：rebase 让分支线性，但**不** FF merge；worktree + 分支 + backup tag 全保留。
- `--keep-backup`：正常 FF merge + 清理，但**保留** backup tag。
- `--no-rebase`：跳过 8.2 的 rebase（更激进的可选项）；与默认 merge 并用时仅在「已可 FF」时合并，否则停下提示用户先 rebase 或加 `--no-merge`。

开关可组合（如 `--no-merge --keep-backup` 等价 `--no-merge`，因后者本就保留 tag）。

### 2. Step 8 流程分支化 + 对比表

- Step 8 顶部加一张「默认 vs 各选项」对比表（rebase / FF merge / 删 worktree / 删分支 / 删 backup tag 五列）。
- `--no-merge` / `--keep-branch`：跑 8.1 + 8.2（含备份 tag），**跳过 8.3（FF merge）与 8.4（清理）**，改为打印 worktree 路径 / 分支名 / backup tag 三项的保留位置 + 一句「后续手动合并/继续迭代/review 的提示」。
- `--keep-backup`：8.4 清理时**跳过** `git tag -d backup/*`，其余照删；末尾打印保留的 tag 名。
- `--no-rebase`：8.2 跳过 rebase 与备份 tag（无 rebase 即无需兜底 tag），其余按其它开关决定。

**验证**：指令型 skill，靠文档自洽 + 对比表与流程描述一致性人工核对。

---

## #20 — 新建 stack `python-uv-workspace`（最重，含模板 + 两个 skill + 规则文档）

参照单包 `python-uv` 的 fragment 体系，落 uv workspace 多包单仓。

### 20.1 模板文件 `templates/python-uv-workspace/`

- **`stack.yml`**：`default_path: .`（虚拟根落仓库根）、`label`、`description`（注明「与单包 `python-uv` 互斥、二选一」）。
- **`__subpath__/`（落点 `.` → 全部合进项目根 `pyproject.toml`）**：
  - `pyproject.toml.uv-workspace.fragment` → `[tool.uv.workspace] members = ["packages/*"]`
  - `pyproject.toml.uv.fragment` → `[tool.uv] python-preference = "only-managed"`（复用 python-uv）
  - `pyproject.toml.uv-index.fragment` → 清华 index（复用）
  - `pyproject.toml.ruff.fragment` → 复用 + `extend-exclude = ["**/_pb"]`（生成码豁免）
  - `pyproject.toml.pytest.fragment` → `[tool.pytest.ini_options]` 带 `addopts = ["--import-mode=importlib"]` + `pythonpath` / `testpaths` 列全各成员（含「新增成员需在此追加」注释）
  - `pyproject.toml.dependency-groups.fragment` → `[dependency-groups] dev = ["pytest", "pytest-cov", "ruff"]`
  - `.vscode/settings.json.fragment` → `python.analysis.extraPaths`（指向各成员 `src`）+ `python.defaultInterpreterPath`（钉死根 `.venv`），带「按成员增删」注释
- **`__subpath__/packages/`（两个参考成员，演示跨成员依赖）**：
  - `example_core/`：库成员。`pyproject.toml`（`[project]` + `[build-system] uv_build`）、`src/example_core/{__init__.py, geometry.py}`（纯函数）、`tests/test_geometry.py`（**无 `__init__.py`**）。
  - `example_app/`：应用成员。`pyproject.toml` 含 `dependencies = ["example-core"]` + `[tool.uv.sources] example-core = { workspace = true }`、`src/example_app/{__init__.py, main.py}`（import example_core 演示跨成员）、`tests/test_main.py`（无 `__init__.py`）。
  - 顶层 `packages/README.md` 或在两成员各放 README 简述布局约定（择一，倾向 stack 根放一份说明）。

> 成员 `pyproject.toml` 是完整文件（非 fragment），按普通文件直接复制；fragment 仅根级 pyproject 与 `.vscode`。

### 20.2 `bootstrap` skill 接入

`skills/bootstrap/SKILL.md` Step 3.5：

- 触发条件由「选中含 `python-uv`」放宽为「含 `python-uv` **或** `python-uv-workspace`」。
- 加 workspace 分支：**跳过** `uv init --package`（虚拟根无 `[project]`，根 `pyproject.toml` 由 workspace fragments 合并生成）；确保 uv 系 fragments 已合（创建根虚拟 pyproject）后，用 **`uv sync`** 代替 `uv add --dev`（dev group 已在 fragment 内声明，成员自动 editable 装入）。pre-commit 两步不变。

### 20.3 `sync-project-config` skill 接入

`skills/sync-project-config/SKILL.md` 4.1 探测 stack + 4.4 可跑化：

- 4.1：自动发现新 stack（目录级软链，模板新增子目录即可见，通常无需改文档，确认即可）。
- 4.4：同 bootstrap，条件放宽 + workspace 分支（跳过 `uv init`、`uv sync` 代 `uv add --dev`）。

### 20.4 规则文档 `rules/python.md`

§2 后新增一节 **§2.2「多包 uv workspace（escape hatch）」**（§2.1 是 hatchling）：固化虚拟根 / 共享配置上提 / `[tool.uv.sources] workspace=true` / `--import-mode=importlib` + 成员 `tests/` 无 `__init__.py` / `extraPaths` 等要素，并指向 `python-uv-workspace` stack。

### 20.5 项目文档同步

- 项目 `CLAUDE.md` 的 templates 条目补 `python-uv-workspace`。
- `README.md`：新增 stack → `/finish` Step 6 README 触发清单命中（顶层目录结构变化），届时更新「模板/stack」相关段。

### 20.6 验证（TDD：成员包是可测的真代码）

- 在 `/tmp` 临时 scaffold 一份（复制模板 + 合并 fragments 模拟）跑 `uv sync && uv run pytest`，确认：① 工作区可 sync；② 跨成员 `from example_core import ...` 可解析；③ 两成员的 `tests/` 同时被 importlib 模式收集、不撞车。
- 成员的纯函数 `geometry.py` 先写 `test_geometry.py`（红→绿），符合 TDD。

---

## #23 — 关闭为已完成（无代码）

round 33 的合一 `ros2` stack（`templates/ros2/` 含 `ros2_py_pkg` + `ros2_cpp_pkg`，`rules/ros2.md` 已落）已完整覆盖 #23 范围。本轮不写代码，`/finish` 时在 commit body 写 `Closes #23` 并备注「被 round 33 的 Python+C++ 合一 ros2 stack 取代」。

---

## 提交与收尾

- 本轮在 worktree `round36-skill与模板批量清理` 内开发。
- `/finish` 时一并 `Closes #13 #20 #23 #35`（四 issue 同轮关闭），按 finish Step 8 默认收尾（rebase + FF merge + 清理）。

## 风险 / 注记

- **#20 是本轮真正的大头**：除模板文件外要动 `bootstrap` + `sync-project-config` 两个 skill 的可跑化逻辑（虚拟根不能 `uv init --package`），比「简单修改」重。若想压缩，可退化为 issue 的方案 B（仅 `rules/python.md` escape hatch 文档），但那样 `/sync-project-config` 接不住——已与你确认走完整 A，故按上文执行。
- 三个 skill（start/finish/bootstrap/sync）均为指令型，无可执行单测，靠文档自洽；#20 模板成员包有真实 pytest 做 happy-path 验证。
