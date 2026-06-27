# packages/ — uv workspace 成员

本目录每个子目录是 workspace 的一个**成员包**，由根 `pyproject.toml` 的
`[tool.uv.workspace] members = ["packages/*"]` 自动纳入同一工作区（一份 lockfile、一个 `.venv`）。

## 参考成员（可删 / 可重命名 / 可照抄）

- **`example_core/`** — 库成员：放可独立单测的纯逻辑（`geometry.py` 纯函数）。无对外脚本。
- **`example_app/`** — 应用成员：依赖 `example_core`，演示**跨成员 import**。依赖关系经各成员
  `pyproject.toml` 的 `dependencies = ["example-core"]` + `[tool.uv.sources] example-core = { workspace = true }`
  解析到本仓库内的源码，而非去 index 拉。

## 新增成员检查清单

1. 在 `packages/<new_member>/` 建标准 src 布局：`pyproject.toml` + `src/<pkg>/__init__.py` + `tests/`。
2. 成员 `pyproject.toml`：`[project]`（name 用连字符、模块用下划线，二者经 uv_build 自动对应）+
   `[build-system] uv_build`。跨成员依赖再加 `dependencies` + `[tool.uv.sources] <dep> = { workspace = true }`。
3. **`tests/` 不放 `__init__.py`**（配合根 `addopts = ["--import-mode=importlib"]` 防同名 tests 包碰撞）。
4. 在**根** `pyproject.toml` 的 `[tool.pytest.ini_options]` 的 `pythonpath` / `testpaths` 各追加本成员的
   `src` / `tests`；在根 `.vscode/settings.json` 的 `python.analysis.extraPaths` 追加本成员 `src`。
5. 仓根 `uv sync` 拉入新成员，`uv run pytest` 跑全树。

> `[build-system] requires` 里的 `uv_build` 版本范围会随 uv 升级偶尔过时，需人工 bump（与 react-vite
> 模板写死 npm 依赖版本同理）。
