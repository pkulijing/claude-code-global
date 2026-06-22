"""ROS 冒烟：节点能 import + 构造（需 rclpy；无 rclpy 的环境整文件 skip）。

抓的是装配错误（missing import / 参数顺序 / self.X 未初始化），不验业务正确性。
"""

import pytest

rclpy = pytest.importorskip("rclpy")

from ros2_py_pkg.talker_node import TalkerNode  # noqa: E402


def test_node_constructs():
    rclpy.init()
    try:
        node = TalkerNode()
        node.destroy_node()
    finally:
        rclpy.shutdown()
