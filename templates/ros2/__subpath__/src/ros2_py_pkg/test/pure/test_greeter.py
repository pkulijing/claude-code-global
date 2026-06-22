"""纯逻辑单测：不依赖 ROS，任意环境可跑（含 macOS）。

跑法（无 ROS 环境）：PYTHONPATH=<pkg-dir> pytest <pkg>/test/pure
跑法（容器/真机）：colcon test 或 pytest <pkg>/test
"""

from ros2_py_pkg.greeter import greeting


def test_greeting_basic():
    assert greeting("alice", 1) == "hello alice #1"


def test_greeting_blank_falls_back_to_world():
    assert greeting("  ", 3) == "hello world #3"
