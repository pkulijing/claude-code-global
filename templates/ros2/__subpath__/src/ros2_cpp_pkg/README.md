# ros2_cpp_pkg —— ROS 2 ament_cmake 参考包

`ros2` stack 模板提供的 **C++ 参考包骨架**，演示 ament-first CMake 约定。用法二选一：

1. **改造成你的包**：把 `ros2_cpp_pkg`（目录名、`include/ros2_cpp_pkg/`、`package.xml` 的 `<name>`、
   `CMakeLists.txt` 的 `project()`、各源码 namespace 与 `#include` 路径）全部替换为你的包名——三处命名
   （目录 / `<name>` / `project()`）必须一致。
2. **当样板**：`ros2 pkg create --build-type ament_cmake <name>` 后，照本包的分层与 CMake 结构补齐。

## 约定（本模板固化）

- **纯逻辑 / ROS 薄壳分层**：可独立验证的逻辑放纯函数（见 `include/ros2_cpp_pkg/greeter.hpp` +
  `src/greeter.cpp`，不依赖 rclcpp、gtest 可单测），节点（`talker_node.*`）只收发翻译，`main.cpp` 仅
  init / spin / shutdown。
- **ament-first CMake**：`ament_cmake` 最先 `find_package`、`ament_package()` 最后且唯一；依赖**消费三步法**
  （`package.xml` 声明 → `find_package` → 链接到目标）；依赖**导出**（`ament_export_targets` +
  `ament_export_dependencies`）让下游链接本包 PUBLIC 接口时找得到目标与传递依赖。
- **PUBLIC/PRIVATE**：公共头 `#include <rclcpp/...>` → `PUBLIC`（故库对 rclcpp/std_msgs 是 PUBLIC 依赖、需导出）；
  仅 `.cpp` 内部用 → `PRIVATE`；可执行 `talker` 私链库 → `PRIVATE`。
- **安装路径约定**：库 → `lib/`、可执行节点 → `lib/<pkg>/`、头 → `include/<pkg>`、launch/config → `share/<pkg>/`。
- **CXX_FLAGS 追加不覆盖**：若需设 `CMAKE_CXX_FLAGS` 必须带 `${CMAKE_CXX_FLAGS}`；本骨架优先用
  `target_compile_*` 避免全局污染。
- **格式/检查用 clang-format**（工作区根 `.clang-format`），不强制 ament_uncrustify / ament_cpplint
  （故 `package.xml` 只 `test_depend` gtest）。
- **不硬编码架构 / 绝对路径**，第三方 SDK 用相对路径 + `CACHE PATH` + 架构分支 + 条件编译 + rpath，保持交叉编译友好。

## 构建 / 运行 / 测试

```bash
colcon build --symlink-install --packages-select ros2_cpp_pkg
source install/setup.bash
ros2 run ros2_cpp_pkg talker                 # 或：ros2 launch ros2_cpp_pkg talker.launch.py

# 测试默认关（BUILD_TESTING=0），显式打开：
colcon test --packages-select ros2_cpp_pkg --cmake-args -DBUILD_TESTING=ON
colcon test-result --verbose
```

> 新增包前对照工作区规则的「新增包检查清单」（`playbooks/ros2.md`）。
