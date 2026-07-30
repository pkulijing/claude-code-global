# ros2_py_pkg —— ROS 2 ament_python 参考包

`ros2` stack 模板提供的 **Python 参考包骨架**，演示约定。用法二选一：

1. **改造成你的包**：把 `ros2_py_pkg`（目录名、内层模块目录、`resource/ros2_py_pkg`、`package.xml` /
   `setup.py` / `setup.cfg` 里的同名串）全部替换为你的包名。
2. **当样板**：`ros2 pkg create --build-type ament_python <name>` 后，照本包的分层与配置补齐。

## 约定（本模板固化）

- **纯逻辑 / ROS 薄壳分层**：可独立验证的逻辑放纯函数（见 `greeter.py`），节点（`talker_node.py`）只收发翻译。
  好处：`test/pure/` 不依赖 ROS、可在任意机器（含 macOS）快测；`test/` 里的 ROS 测在容器 / 真机跑。
- **install() 卫生**：`setup.py` 的 `data_files` 装 resource marker + package.xml + launch；
  `entry_points.console_scripts` 暴露可执行——确保 `colcon build --install` 能把包打进二进制版本。
- **lint / format 用 ruff**（工作区根 `ruff.toml`），不强制 ament_flake8 / pep257（故 package.xml 只
  test_depend pytest）。
- **不硬编码架构 / 绝对路径**，保持交叉编译（aarch64）友好。

## 构建 / 测试

```bash
colcon build --symlink-install --packages-select ros2_py_pkg
colcon test --packages-select ros2_py_pkg     # 或免 ROS 快测纯逻辑：见下
PYTHONPATH=src/ros2_py_pkg uv run pytest src/ros2_py_pkg/test/pure -q
```

> 新增包前对照工作区规则的「新增包检查清单」（`playbooks/ros2.md`）。
