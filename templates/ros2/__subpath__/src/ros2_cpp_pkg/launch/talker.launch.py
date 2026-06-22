"""最小 launch 示例：拉起 talker 节点并演示传参。

安装到 share/<pkg>/launch/（见 CMakeLists 的 install(DIRECTORY launch ...)）。
跑法：ros2 launch ros2_cpp_pkg talker.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="ros2_cpp_pkg",
                executable="talker",
                name="talker",
                parameters=[{"name": "ros2", "period_s": 1.0}],
            ),
        ]
    )
