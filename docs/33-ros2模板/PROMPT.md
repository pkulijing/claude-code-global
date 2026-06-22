# PROMPT —— ROS 2 工作空间脚手架模板

## 背景

`claude-code-global` 的 `templates/` 已沉淀两个开箱即用脚手架：后端 `python-uv`（落根）、前端 `react-vite`（落 `frontend/`），由 `bootstrap` / `sync-project-config` 消费。每个 stack 配一份领域规则文档（`rules/python.md` / `rules/frontend.md`），由 `GLOBAL_AGENTS.md` 顶层指针引用。

现需新增对 **ROS 2** 工程的支持。用户此前已在实践中攒了一个 `ros2-python` 初版（未提交，现位于 `templates/ros2-python/`），并提供了一份团队的《软件构建集成规范》作为权威输入。

## 输入材料

### 1. 集成文档（Anyverse《软件构建集成规范》）

来源：飞书 wiki `https://qcn4se3qlil6.feishu.cn/wiki/HhVZwyE37i4ob6kOxCUcyQIMnFg`。要点：

- **工作空间结构**：一个 colcon 工作空间内含多个 ROS 2 包（`src/` 基础公共包、`sub_modules/` 独立功能包），统一构建入口、产品级配置、`.ws/` 构建输出。
- **包类型**（同一工作空间内并存）：C++ 功能包（`ament_cmake`）、消息/服务包（`ament_cmake` + `rosidl`）、Bringup 配置包（仅 install）、Python 包（`ament_python`）。
- **package.xml 规范**：`format="3"`，包名小写+下划线且与目录名 / `project()` 一致，`<depend>` / `<build_depend>` / `<exec_depend>` / `<test_depend>` 分场景，语义化版本。
- **CMakeLists.txt 规范（ament 优先）**：标准构建顺序（`ament_cmake` 最先 find、`ament_package()` 最后）、依赖消费三步法（package.xml 声明 → `find_package` → 链接到目标）、依赖导出（`ament_export_targets` / `ament_export_dependencies`）、导入目标命名规则、PUBLIC/PRIVATE 选择、通用 C++ 骨架、`CMAKE_CXX_FLAGS` 必须追加不可覆盖、第三方 SDK 集成规范、安装路径约定（可执行 → `lib/<pkg>/`、库 → `lib/`、头 → `include/`、launch/config → `share/<pkg>/`）。
- **命名约定**：硬件接口 `<device>_hardware`、控制器 `<feature>_controller`、Bringup `<robot>_<variant>_teleop_bringup`、消息包 `<domain>_msgs`。
- **新增包检查清单**：12 条，覆盖三处命名一致、format 3、cmake ≥ 3.16、cxx_std_17、依赖一致、导出齐全、`ament_package()` 唯一且置末、安装路径、第三方 SDK、README、产品白名单、本地验证。

> 注：文档中的 `script/build.sh`、`config/products/*.json`、`cmake/toolchain/`、`.ws/` 等是 Anyverse 仓库特有的「下游集成层」，由各自专属仓库提供，**不属于通用模板范畴**。模板应吸收文档里**可迁移的通用约定**（ament-first CMake、package.xml、install 卫生、命名、检查清单），而非复刻 Anyverse 专属脚本。

### 2. 现有 `ros2-python` 初版（未提交）

`templates/ros2-python/`：已是标准 stack 形态——`stack.yml`（`default_path: .`）+ `__root__`（`.gitignore` / `ruff.toml` / `.vscode` fragment）+ `__subpath__/ros2_py_pkg/`（一个 `ament_python` 参考包，含「纯逻辑 `greeter.py` / ROS 薄壳 `talker_node.py`」分层、install 卫生的 `setup.py`、纯逻辑单测 + ROS 冒烟测试）。质量良好，遵循 `rules/python.md` 的分层与测试约定，可作为合并后 stack 的 Python 参考包基底。

## 需求

1. 参考集成文档，把 ROS 2 工程脚手架做成 `templates/` 下的可消费 stack，覆盖 **Python（`ament_python`）与 C++（`ament_cmake`）两类包**。
2. **可组合性**是硬约束：一个代码仓库可以包含多个 ROS 包（既有 Python 也有 C++），它们共享同一个 colcon 工作空间与工作区级配置。模板机制下，两个都落工作空间根（`default_path: .`）的独立 stack 会在 `__root__` 撞车，无法干净并存。
3. 因此核心设计问题：**是否把 `ros2-python` 与 `ros2-c++` 合并为单一 `ros2` stack**（工作区级配置在 `__root__`，Python 与 C++ 参考包并列在 `__subpath__`），而非两个独立 stack？—— 用户倾向合并，待 PLAN 决议确认。
4. 与现有两个 stack 对称，预期还应产出一份 **`rules/ros2.md`** 领域规则文档（把集成文档的通用约定固化），并在 `GLOBAL_AGENTS.md` 加指针 + 触发条件。

## 约束

- 模板内容遵循集成文档的 ament-first 约定与新增包检查清单；C++ 参考包要能体现依赖消费/导出、install 路径、纯逻辑/薄壳分层。
- 遵循 `rules/python.md`（Python 参考包）与本轮新增 `rules/ros2.md`（ROS 约定）。
- 注释写「当前真相 / WHY」，不绑定开发历史、不复刻 Anyverse 专属下游脚本。
- 不强行引入重型 ROS 工具链依赖到模板本身；模板是「脚手架 + 约定」，真实构建在装了 ROS 2 的机器 / 容器里跑。
