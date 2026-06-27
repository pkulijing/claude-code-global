# Round 36 — skill 与模板批量清理

本轮批量处理 4 条积压 issue，定位「清理一些文档、skill、模板类型的修改」。逐条来源与处理结论如下。

## #13 — `/finish` 支持 `--no-merge` / `--keep-branch` / `--keep-backup` 选项

> 来自 [#13 /finish 支持 --no-merge / --keep-branch / --keep-backup 选项，免去用户每次手工说明](https://github.com/pkulijing/claude-code-global/issues/13)
> Labels: `type:feat` `area:skill` `priority:P2`

`/finish` Step 8（worktree 收尾）默认「rebase → FF merge → 删 worktree → 删分支 → 删 backup tag」一站到底。但存在合理变体：发包/外审前想保留分支不立即并入 master、想继续迭代、高风险轮想多保 backup tag。目前这三种诉求每次都得用户在调用时手工说明，未规约化、易遗忘、CC 也可能误解。

**落点**：`skills/finish/SKILL.md` ARGUMENTS 处理段 + Step 8 流程加入开关支持，并补一张「默认行为 vs 各选项行为」对比表。

## #20 — 把 uv packages monorepo 布局沉淀成模板（完整 A：新建 stack）

> 来自 [#20 把 uv packages monorepo 布局沉淀成模板](https://github.com/pkulijing/claude-code-global/issues/20)
> Labels: `type:feat` `area:template` `priority:P2`

`teleop-operator` 把单包仓升级成 uv workspace 多包单仓（虚拟根 + 一份 lockfile，成员落 `packages/*`），目前是手搓 ad-hoc 布局，不归属任何 stack，`/sync-project-config` 接不住。本轮按用户决策走**完整 A**：新建 stack `python-uv-workspace`（与单包 `python-uv` 并列、二选一）。

实战提炼、模板需固化的关键要素：

- **虚拟根**：根 `pyproject.toml` 无 `[project]`，仅 `[tool.uv.workspace] members = ["packages/*"]`。
- **共享配置上提到根**：`[tool.uv]`（only-managed + 清华 index）/ `[dependency-groups] dev` / `[tool.ruff]` 都在根，成员不重复。
- **各成员独立 `pyproject.toml`**，跨成员依赖走 `[tool.uv.sources] <dep> = { workspace = true }`。
- 仓根一条 `uv run pytest` 跑全树，配 `[tool.pytest.ini_options] addopts = ["--import-mode=importlib"]`，各成员 `tests/` 不放 `__init__.py`。
- `pythonpath` / `testpaths` 列全各成员 `src` / `tests`；生成码（protobuf `_pb`）`ruff extend-exclude`。
- **`.vscode/settings.json` 带 `python.analysis.extraPaths` 指向各成员 `src`** + `python.defaultInterpreterPath` 钉死根 `.venv`。

**落点**：`templates/python-uv-workspace/`（stack.yml + fragments + 参考成员包）；`bootstrap` / `sync-project-config` skill 接入；`rules/python.md` §2 补一节「多包 workspace」escape hatch；项目 `CLAUDE.md` / `README.md` 同步。

## #23 — ROS2 stack 模板（关闭为已完成）

> 来自 [#23 新增 ROS2 stack 模板：ros2-python（已落）+ ros2-cpp（待补）](https://github.com/pkulijing/claude-code-global/issues/23)
> Labels: `type:feat` `area:template` `priority:P2`

issue 当时规划「ros2-python 先落、ros2-cpp 下一轮补」。**round 33 已把二者合一**：`templates/ros2/` 单一 stack 同时含 `ros2_py_pkg`（ament_python）与 `ros2_cpp_pkg`（ament_cmake），`rules/ros2.md` 也已落地（一个仓库即一个 colcon 工作空间、Python + C++ 并存，拆两 stack 会在 `__root__` 撞车，故合一更对）。issue 范围已被完整覆盖。

**处理**：本轮不写代码，`/finish` 时 `Closes #23` 并说明被 round 33 的合一 stack 取代。

## #35 — `/start` 并行 worktree 下 round 编号撞车

> 来自 [#35 start：并行 worktree 下 round 编号撞车，多轮被识别成同一个 N](https://github.com/pkulijing/claude-code-global/issues/35)
> Labels: `type:bug` `area:skill` `priority:P1`

`skills/start/SKILL.md` Step 1 算 N 只「扫 `docs/` 取最大值 +1」。并行 worktree 里新建的 `docs/N-*` 尚未合入主分支、其它 worktree 看不见，于是各 round 独立算出同一个 N+1，合入时要手动纠正目录名/分支名/文档轮次号。

**落点**：`skills/start/SKILL.md` Step 1，编号识别信号源补上「其它在途 worktree 已占用的 N」——并集来自 ① 本地 `docs/N-*` ② `round<N>-*` 分支名解析 ③ `git worktree list` 各 worktree 的 `docs/N-*`，取最大值 +1，解析失败跳过不报错。
