// 纯逻辑示例（C++ 侧）：与 ROS 解耦，故 gtest 可独立单测、下游可直接复用。
// 约定：把可独立验证的业务逻辑放进这类纯函数 / 类，ROS 节点只做收发翻译——
// 便于 TDD、便于在无运行时 ROS 上下文的情况下测（见 test/test_greeter.cpp）。
#ifndef ROS2_CPP_PKG__GREETER_HPP_
#define ROS2_CPP_PKG__GREETER_HPP_

#include <string>

namespace ros2_cpp_pkg
{
/// 生成第 count 条问候语（纯函数）。name 去首尾空白后为空则回退 "world"。
std::string greeting(const std::string & name, int count);
}  // namespace ros2_cpp_pkg

#endif  // ROS2_CPP_PKG__GREETER_HPP_
