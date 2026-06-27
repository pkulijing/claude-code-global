# ROS 2 开发规则

> 本文档由 `claude-code-global` 仓库的 `rules/ros2.md` 提供，经 `install.sh` 双轨软链到 `~/.claude/rules/ros2.md`（CC 端）与 `~/.codex/rules/ros2.md`（Codex 端）。修改请回到 `claude-code-global` 仓库，不要直接编辑软链目标。
>
> **触发条件**：Coding Agent 在本轮任务涉及 ROS 2 工程、colcon 工作空间、ament（`ament_cmake` / `ament_python`）、`package.xml`、`CMakeLists.txt`（ROS 包）、launch 文件或 ROS 包构建/依赖判断时，**必须先把本文件读入上下文**，再开始动手。

ROS 2 是一个**工作空间（colcon workspace）维度**：一个仓库即一个工作空间，可含多个 ROS 2 包（C++ `ament_cmake` 与 Python `ament_python` 并存）。本规则与后端语言（Python / 前端）维度正交。配套脚手架是 `ros2` stack 模板（`bootstrap` / `sync-project-config` 消费），工作区级配置落仓库根、参考包落 `src/`。

> **本规则的边界**：下沉的是**通用、可迁移**的 ROS 2 / ament 约定。各团队监仓特有的「下游集成层」——统一构建入口 `script/build.sh`、产品化配置 `config/products/*.json`、交叉编译工具链 `cmake/toolchain/`、`.ws/` 输出目录等——由各自专属仓库与文档提供，不属于本规则或 `ros2` 模板范畴；命中这类下游集成时以该仓库自己的文档为准。

## 1. 工作空间与布局

- **colcon 工作空间**：包放 `src/`（标准 colcon 布局，`colcon build` 从工作空间根递归发现 `src/` 下各 `package.xml`）。`build/`、`install/`、`log/`（及部分团队统一构建入口用的 `.ws/`）为产物，全部 gitignore。
- **包 = 含 `package.xml` 的独立目录、colcon 可发现**——这是唯一硬约定，父目录名不限。部分监仓按用途再分（如基础公共包放 `src/`、独立功能包放 `sub_modules/`），二者都是合法 scan root；脚手架默认用标准 `src/`。
- **clangd**：构建产出的 `compile_commands.json` 合并后在仓库根软链一份供 clangd 使用（属产物、gitignore）。

## 2. 包类型

| 类型           | build_type                  | 典型用途                    |
| -------------- | --------------------------- | --------------------------- |
| C++ 功能包     | `ament_cmake`               | 节点、库、控制器、硬件接口  |
| 消息/服务包    | `ament_cmake` + `rosidl`    | `.msg` / `.srv` / `.action` |
| Bringup 配置包 | `ament_cmake`（仅 install） | launch、config、urdf、脚本  |
| Python 包      | `ament_python`              | 纯 Python 节点              |

## 3. package.xml 规范

- 统一 `format="3"`。
- 包名小写 + 下划线，**与目录名、`project()`（C++）三者一致**。
- 依赖标签按场景：`<depend>`（编译 + 链接 + 运行都要）、`<build_depend>`（仅编译期）、`<exec_depend>`（仅运行期，如 launch 拉起其他包 / 解释器）、`<test_depend>`（仅测试）。
- 版本号语义化 `MAJOR.MINOR.PATCH`。
- 控制器 / 硬件接口在 `<export>` 中声明 plugin XML 路径。

## 4. CMakeLists.txt 规范（ament 优先）

**核心原则**：以 ROS 2 `ament_cmake` 官方约定为首要准则，团队特有模式（第三方 SDK、调试开关等）在此基础上**扩展**。

### 4.1 标准构建顺序

`cmake_minimum_required`（≥ 3.16）/ `project` → `find_package(ament_cmake REQUIRED)`（**必须最先 find**）→ `find_package(<各依赖> REQUIRED)` → `add_library` / `add_executable` → `ament_target_dependencies` / `target_link_libraries` → `install(TARGETS ... EXPORT ...)` → `ament_export_targets` / `ament_export_dependencies` → `ament_package()`（**必须最后且仅一次**）。

### 4.2 添加依赖（消费方）— 三步缺一不可

1. **package.xml 声明**（见 §3 标签语义）。
2. **CMakeLists `find_package`**：惯用
   ```cmake
   set(THIS_PACKAGE_INCLUDE_DEPENDS rclcpp std_msgs ...)
   find_package(ament_cmake REQUIRED)
   foreach(Dependency IN ITEMS ${THIS_PACKAGE_INCLUDE_DEPENDS})
     find_package(${Dependency} REQUIRED)
   endforeach()
   ```
3. **链接到目标**：`ament_target_dependencies`（ROS/ament 包**首选**，自动附加 include/link/definitions）；`target_link_libraries`（精确控制链接顺序、第三方 SDK、消息生成目标）。

**导入目标命名**：普通 ament C++ 库 `rclcpp::rclcpp` / `cv_bridge::cv_bridge`；消息/服务包 `${sensor_msgs_TARGETS}` / `${my_msgs_TARGETS}`；本仓库 ament 库 `mypkg::mypkg`；系统/CMake 包 `Boost::system` / `OpenSSL::Crypto` / `yaml-cpp`。

**PUBLIC/PRIVATE**：公共头 `#include <rclcpp/...>` → `PUBLIC`；仅 `.cpp` 内部用 → `PRIVATE`；第三方预编译 `.so` → `PRIVATE`（不走 `ament_target_dependencies`）。

### 4.3 导出依赖（提供方）

**规则**：导出所有「下游链接本包 PUBLIC 接口时必须能找到」的 ament 依赖；系统库（Boost、OpenSSL、第三方 `.so`）通常不导出。

- `ament_export_targets(export_<pkg> HAS_LIBRARY_TARGET)` —— 导出 CMake 导入目标（**推荐**，控制器 / 硬件接口）。
- `ament_export_libraries(...)` —— 导出库文件路径列表（简单库可用）。
- `ament_export_include_directories(...)` —— 有公共 `include/` 时配合。
- `ament_export_dependencies(...)` —— 告知下游需 `find_package` 的依赖（**必须**）。

各类型包导出要点：C++ 库/节点包 `ament_export_*` + `ament_export_dependencies`；消息包 `ament_export_dependencies(rosidl_default_runtime)`；Bringup 包仅 `ament_package()`；插件包额外 `pluginlib_export_plugin_description_file(...)`。

### 4.4 安装路径约定

| 产物            | 安装位置                 |
| --------------- | ------------------------ |
| 共享库          | `lib/`                   |
| 可执行节点      | `lib/<package_name>/`    |
| 头文件          | `include/<package_name>` |
| launch / config | `share/<package_name>/`  |

### 4.5 CXX_FLAGS 与第三方 SDK

- **`CMAKE_CXX_FLAGS` 必须追加不可覆盖**：`set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17 -O3")`（✅），直接覆盖 `set(CMAKE_CXX_FLAGS " -std=c++17 -O3")`（❌，会冲掉上游/工具链注入的 flag）。优先用 `target_compile_*` 施加，避免全局污染。
- `target_compile_features(<tgt> PUBLIC cxx_std_17)`（或更高）。
- **第三方 SDK**：路径用 `CACHE PATH` + 相对路径；架构分支用 `CMAKE_SYSTEM_PROCESSOR` 区分 x86_64 / aarch64；缺失用 `WARNING` + 条件编译不阻断整包；功能开关用 `option(ENABLE_XXX ...)` + `target_compile_definitions`；动态库 `target_link_libraries(... PRIVATE ...)` 并设 RPATH。

## 5. Python / pip 依赖（ament_python 包消费 pip 依赖）

任何 ROS 2 工程都会遇到「一个 ROS 包怎么装它的 pip 依赖」。与 §4 的 C++（CMake / ament）依赖并列，Python 依赖的选型默认走轻方案：

- **默认：`requirements.txt` + 一条 `pip install -r requirements.txt`**。公网包走团队源（清华）；私有包在 `requirements.txt` 顶部加 `--extra-index-url`（含只读 token）+ `--trusted-host` 两行即可。这是兄弟仓 `record_agent`（同为 `ament_python` + pip 依赖）的既有做法，简单可靠。
- **rosdep 自定义 yaml 是重武器，仅必须时用**：只有当确需让 `rosdep install` 解析私有 key（如 CI 强制全程走 rosdep）时才上。坑有二，配套成本不低：
  - rosdep 的 pip installer 用 `sudo -H --preserve-env=... pip3 install` 跑，会**剥掉** `PIP_CONFIG_FILE` / `PIP_TRUSTED_HOST` 等环境变量 → 私有 index / 自签证书全失效；需 sudoers `env_keep` 显式穿透。
  - pip 配置文件里的 `trusted-host` **不被** pip 的下载会话采纳（只有命令行 flag / `PIP_TRUSTED_HOST` env 生效）。
- **一句话原则：选型前先看兄弟仓既有做法**，别凭「更正规」的直觉直接上重机制——重武器的隐性成本（registry index + token + 跳过自签证书 + sudoers）往往远超「requirements.txt 顶部两行」。

## 6. 纯逻辑 / ROS 薄壳分层（跨语言通用）

呼应 `rules/python.md` §3 的 OO/分层偏好，ROS 包同样遵循：

- **可独立验证的业务逻辑放纯函数 / 纯类**（不依赖 rclcpp / rclpy），ROS 节点只做收发翻译与定时。
- 好处：纯逻辑可在无运行时 ROS 上下文下单测（Python 侧 `test/pure/` 在任意机器含 macOS 快测；C++ 侧 gtest 不必拉起节点）；装配错误（missing include / 参数顺序 / 成员未初始化）由 build 期与节点冒烟抓出。
- C++ 把节点声明放公共头时，其 PUBLIC 依赖（rclcpp / 消息包）要进 `ament_target_dependencies(PUBLIC ...)` 并 `ament_export_dependencies`。

## 7. 测试

- 跑测试：`colcon test`，结果 `colcon test-result --verbose`。
- C++ 用 `ament_add_gtest`（`find_package(ament_cmake_gtest REQUIRED)`，`test/` 下 gtest 源）。注意统一构建系统常把全局 `BUILD_TESTING` 默认设 `0`，需 `--cmake-args -DBUILD_TESTING=ON`（或团队构建脚本的 `-d BUILD_TESTING=ON`）显式打开。
- Python 包测试细则（pytest / 纯逻辑分层 / 编排器 happy-path）遵循 `rules/python.md` §4；ROS 节点至少有一条「能 import + 构造」的冒烟测试（无 rclpy 环境用 `pytest.importorskip` 整文件 skip）。

## 8. 新增包检查清单

新增 ROS 2 包前逐条核对：

- [ ] 目录名、`package.xml` `<name>`、`project()`（C++）三者一致
- [ ] `package.xml` 用 `format="3"`，声明所有依赖（标签语义正确）
- [ ] C++：`cmake_minimum_required` ≥ 3.16
- [ ] C++：`target_compile_features(... cxx_std_17)` 或更高
- [ ] `package.xml` 与 `CMakeLists.txt`（C++）依赖一致
- [ ] `ament_export_dependencies` 覆盖所有 PUBLIC ament 依赖
- [ ] `ament_package()` 在文件末尾且仅调用一次
- [ ] 可执行节点安装到 `lib/<package_name>/`，launch/config 安装到 `share/<package_name>/`
- [ ] 第三方 SDK：相对路径 + `CACHE` + 条件编译 + rpath
- [ ] 提供 `README.md` 说明构建命令与关键选项
- [ ] 纯逻辑与 ROS 薄壳分层，纯逻辑有单测
- [ ] 本地验证可构建可跑（`colcon build` / `colcon test`，或团队统一构建入口）

## 9. 构建

- 通用：`colcon build --symlink-install`；按包构建 `--packages-select <pkg>`；测试 `colcon test`。
- 团队监仓若提供统一构建入口（如 `script/build.sh`），优先走它（便于 ccache / clang / 交叉编译 / 产品化打包等下游优化）——具体参数以该仓库文档为准，本规则不复刻。
