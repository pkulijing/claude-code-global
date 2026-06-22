#include "ros2_cpp_pkg/talker_node.hpp"

#include <chrono>
#include <string>

#include "ros2_cpp_pkg/greeter.hpp"

namespace ros2_cpp_pkg
{
TalkerNode::TalkerNode()
: rclcpp::Node("talker")
{
  name_ = declare_parameter<std::string>("name", "world");
  const double period_s = declare_parameter<double>("period_s", 1.0);
  pub_ = create_publisher<std_msgs::msg::String>("chatter", 10);
  timer_ = create_wall_timer(
    std::chrono::duration<double>(period_s), [this]() { tick(); });
  RCLCPP_INFO(get_logger(), "talker up -> /chatter every %.3gs", period_s);
}

void TalkerNode::tick()
{
  std_msgs::msg::String msg;
  msg.data = greeting(name_, ++count_);
  pub_->publish(msg);
}
}  // namespace ros2_cpp_pkg
