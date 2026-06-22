"""纯逻辑示例：与 ROS 解耦，故可在任意环境（含 macOS，无需 rclpy）单测。

约定：把可独立验证的业务逻辑放进这类纯函数 / 类，ROS 节点只做收发翻译——
便于 TDD，便于在无 ROS 的机器上快测（见 test/pure/）。
"""

from __future__ import annotations


def greeting(name: str, count: int) -> str:
    """生成第 count 条问候语（纯函数）。"""
    who = name.strip() or "world"
    return f"hello {who} #{count}"
