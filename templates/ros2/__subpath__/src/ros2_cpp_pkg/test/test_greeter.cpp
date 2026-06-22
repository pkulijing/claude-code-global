// 纯逻辑单测（gtest）：greeter 不依赖 rclcpp，断言其问候语契约。
// 由 CMakeLists 的 ament_add_gtest 接入；BUILD_TESTING 默认关，用 -d BUILD_TESTING=ON 开。
// 跑法：colcon test --packages-select ros2_cpp_pkg --cmake-args -DBUILD_TESTING=ON
#include <gtest/gtest.h>

#include "ros2_cpp_pkg/greeter.hpp"

TEST(GreeterTest, BasicGreeting)
{
  EXPECT_EQ(ros2_cpp_pkg::greeting("alice", 1), "hello alice #1");
}

TEST(GreeterTest, BlankNameFallsBackToWorld)
{
  EXPECT_EQ(ros2_cpp_pkg::greeting("  ", 3), "hello world #3");
}
