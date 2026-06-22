// 可执行入口（薄 main）：仅 init / spin / shutdown，节点逻辑在 TalkerNode。
// 安装到 lib/<package_name>/（见 CMakeLists），由 `ros2 run ros2_cpp_pkg talker` 拉起。
#include <memory>

#include "rclcpp/rclcpp.hpp"

#include "ros2_cpp_pkg/talker_node.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ros2_cpp_pkg::TalkerNode>());
  rclcpp::shutdown();
  return 0;
}
