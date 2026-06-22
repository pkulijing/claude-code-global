"""最小 rclpy 节点：定时 publish std_msgs/String。

演示「ROS 薄壳 + 纯逻辑分层」：消息内容由纯函数 greeting() 产出（可单测），节点只管收发与定时。
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from ros2_py_pkg.greeter import greeting


class TalkerNode(Node):
    def __init__(self) -> None:
        super().__init__("talker")
        self._name = self.declare_parameter("name", "world").value
        self._pub = self.create_publisher(String, "chatter", 10)
        self._count = 0
        period = self.declare_parameter("period_s", 1.0).value
        self.create_timer(period, self._tick)
        self.get_logger().info(f"talker up → /chatter every {period}s")

    def _tick(self) -> None:
        self._count += 1
        msg = String()
        msg.data = greeting(self._name, self._count)
        self._pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TalkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
