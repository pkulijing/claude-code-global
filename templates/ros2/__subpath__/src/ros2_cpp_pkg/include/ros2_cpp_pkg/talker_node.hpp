// 最小 rclcpp 节点：定时 publish std_msgs/String。
// 演示「ROS 薄壳 + 纯逻辑分层」：消息内容由纯函数 greeting() 产出（可单测），节点只管收发与定时。
// 本头公开 #include <rclcpp/...>，故 rclcpp / std_msgs 是库的 PUBLIC 依赖——对应 CMakeLists 里
// ament_target_dependencies(... PUBLIC ...) 与 ament_export_dependencies(...)。
#ifndef ROS2_CPP_PKG__TALKER_NODE_HPP_
#define ROS2_CPP_PKG__TALKER_NODE_HPP_

#include <string>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

namespace ros2_cpp_pkg
{
class TalkerNode : public rclcpp::Node
{
public:
  TalkerNode();

private:
  void tick();

  std::string name_;
  int count_{0};
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};
}  // namespace ros2_cpp_pkg

#endif  // ROS2_CPP_PKG__TALKER_NODE_HPP_
