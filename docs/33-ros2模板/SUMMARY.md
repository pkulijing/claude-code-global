# SUMMARY —— ROS 2 工作空间脚手架模板

## 开发项背景

`claude-code-global` 的 `templates/` 已有后端 `python-uv`、前端 `react-vite` 两个开箱即用 stack，每个配一份 `rules/*.md` 领域规则。本轮要新增对 **ROS 2** 工程的支持。

输入有二：① 用户此前攒的未提交 `ros2-python` 初版（`templates/ros2-python/`，质量良好）；② 团队《软件构建集成规范》（飞书 wiki），一份覆盖工作空间结构、统一构建系统、4 种包类型、ament-first CMake 规范、产品化构建、交叉编译、新增包检查清单的权威文档。

要解决的核心问题：**一个代码仓库可以包含多个 ROS 包（既有 Python 也有 C++）**，它们共享同一 colcon 工作空间与工作区级配置。该如何组织模板，使两类包能干净并存、可组合？

## 实现方案

### 关键设计

1. **合并为单一 `ros2` stack，而非 `ros2-python` + `ros2-c++` 两个**。
   决定性依据来自模板机制本身：`__subpath__` 落点由 `default_path` 决定，而 ROS 工作空间的 Python 包与 C++ 包都落工作空间根（`default_path: .`）。若拆成两个 stack，二者都要在 `__root__` 贡献同名工作区配置（`.gitignore` / `.vscode/*` / 工作区级 lint 配置），必然撞车（机制只规定「stack 优先」、未定义两个 ros2 stack 谁赢）。
   正确抽象是：**stack 的单位是「colcon 工作空间」，不是「语言」**——这与集成文档「一个工作空间内 4 种包类型并存」的事实一致。故单一 `ros2` stack：工作区级配置落 `__root__`，Python 与 C++ 参考包并列在 `__subpath__/src/`，一次 adopt 即得完整工作空间脚手架。

2. **参考包落 `src/`（标准 colcon 布局）**。
   过程中复核了「加 `src/` 是否违反集成文档」：结论是**非但不违反，文档自身就用 `src/`**——文档第一节工作空间结构把基础包放 `src/`、功能包放 `sub_modules/`，唯一硬约定是「每个包是含 `package.xml` 的独立目录、colcon 可发现」，对父目录名无限制；构建示例的 `-s <base>` 参数也印证包活在某 base 目录下。团队别人的仓库看不到 `src/`，是因为文档「后续结构」走「每个模块独立仓库」——单包仓库无需 `src/` 包裹层；而本模板的目标恰是多包工作空间，`src/` 是标准且文档兼容的选择。

3. **C++ 参考包的「纯逻辑 / ROS 薄壳分层」与文档骨架兼得**。
   库 `ros2_cpp_pkg` 同时编译纯逻辑 `greeter`（不依赖 rclcpp、gtest 可独立测）与节点 `TalkerNode`；节点头公开 `#include <rclcpp/...>`，使 rclcpp/std_msgs 成为库的**真实 PUBLIC 依赖**——于是 `ament_target_dependencies(PUBLIC ...)` 与 `ament_export_dependencies(...)` 的演示是诚实的（不是为演示而虚标依赖）。薄 `main.cpp` 链接库成可执行 `talker`。这样既完整复刻文档第四节的 ament-first 骨架（消费三步法 / 导出 / install 路径 / `ament_package()` 末尾唯一），又保留跨语言通用的分层约定。

4. **配套领域规则 `rules/ros2.md`，与 python.md/frontend.md 对称**。
   模板提供「脚手架」，规则文档固化「约定」——把集成文档里**通用、可迁移**的部分（ament-first CMake、命名、依赖消费/导出、install 路径、新增包检查清单）下沉为 Agent「触发即读」的规则；明确划清边界：`script/build.sh` / 产品 JSON / 交叉编译属团队下游集成层，模板与规则都不复刻。

### 开发内容概括

- **重构**：`templates/ros2-python/` → `templates/ros2/`，参考包迁入 `__subpath__/src/`。
- **`stack.yml`**：改名 `ros2`、`default_path: .`、双语言 label/description，注释解释「为何合并不拆分」。
- **`__root__` 工作区配置**：`.gitignore`（加 `.ws/` + `compile_commands.json` 软链忽略）；新增 `.clang-format`（Google 基线 / 2 空格 / 100 列，呼应 ruff）；`.vscode` 两个 fragment 加 clangd / cmake / ROS 扩展与 C/C++ 作用域设置（与 `[python]` union 共存）；`ruff.toml` 沿用。
- **C++ 参考包 `ros2_cpp_pkg`（新建）**：`CMakeLists.txt`（严格按文档骨架）、`package.xml`（format 3 / ament_cmake / depend rclcpp std_msgs / exec_depend launch\* / test_depend gtest）、`greeter.hpp/.cpp`（纯逻辑）、`talker_node.hpp/.cpp`（薄壳节点）、`main.cpp`、`launch/talker.launch.py`、`test/test_greeter.cpp`（gtest）、`README.md`。
- **Python 参考包 `ros2_py_pkg`**：README 泛化（去掉对具体文档名《产品打包构建说明》的硬绑定，符合 `rules/python.md` §3.4）、构建/测试命令更新为 src/ 布局。
- **`rules/ros2.md`（新建）**：8 节领域规则。
- **`GLOBAL_AGENTS.md`**：rules 清单加 ros2 一行 + 新增「## ROS 2 开发规则」指针段（触发条件）。
- **项目 `CLAUDE.md`**：templates 描述补 `ros2` 维与合并理由。

### 额外产物

- C++ 纯逻辑 `greeter` 经本机 clang 以 `-std=c++17 -Wall -Wextra -Wpedantic` 验证零告警，并用临时 main 跑通与 gtest 等价的契约断言。
- Python 纯逻辑单测在 src/ 布局下 2 passed（验证迁移后 import 干净）。

## 局限性

- **完整 colcon 构建未在本机验证**：开发机无 ROS 2，C++ 节点中依赖 rclcpp/std_msgs 的部分（`talker_node` / `main` / gtest 链接 ament）未实际编译，需在装了 ROS 2 的环境（容器 / 真机）跑 `colcon build` / `colcon test` 做端到端验证。本机只验证了不依赖 ROS 的纯逻辑层。
- **`.clang-format` 未做格式一致性回归**：开发机无 clang-format，未对 C++ 源做 `--dry-run -Werror` 校验，理论上 formatOnSave 首次可能有微调；待 ROS 环境或 CI 首次跑过即稳定。
- **仅覆盖 4 种包类型中的 2 种**：消息包 `*_msgs`、Bringup 包未给脚手架，约定写在 `rules/ros2.md` 但无样板包。

## 后续 TODO

- 在装了 ROS 2 的环境对 `ros2` stack 做一次端到端 adopt + `colcon build --symlink-install` + `colcon test --cmake-args -DBUILD_TESTING=ON`，确认 C++ 包真实可构建可测。
- 视需要补消息包 `*_msgs` 参考（演示跨包消息依赖与 `${pkg_TARGETS}` 链接，文档重点之一）与 Bringup 包参考（仅 install 的 launch/config 包）。
- 待 `bootstrap` / `sync-project-config` 在真实 ROS 项目里消费一次，回看 `__subpath__/src/` 落点与 fragment 合并是否如预期。

## 可沉淀项

本轮即是在向 `claude-code-global` 沉淀模板与规则，产物本身就是跨项目资产，无需再额外提炼「流程类」沉淀项。一条值得记的方法论（非新增资产，属既有约定的再次印证）：

- **「stack 的单位」判定**：当犹豫某能力该拆几个 stack 时，回到模板机制的 `default_path` —— 落点相同（同争 `__root__`）的能力应合并为一个 stack（如本轮 ROS Python + C++ 同落工作空间根 → 合并），落点正交（如前端 `frontend/` vs 后端根）才拆。这条已隐含在 `react-vite`/`python-uv` 的正交设计里，本轮 ROS 是「同落点 → 合并」方向的首个实例，已写进 `stack.yml` 与项目 `CLAUDE.md` 注释，无需再单独提 issue。

故跨仓库可沉淀项：**暂无**（本轮自身即沉淀，自指守卫下也不向本仓 API 自提）。
