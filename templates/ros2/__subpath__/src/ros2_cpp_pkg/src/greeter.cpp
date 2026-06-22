#include "ros2_cpp_pkg/greeter.hpp"

#include <string>

namespace ros2_cpp_pkg
{
namespace
{
std::string trim(const std::string & s)
{
  const auto begin = s.find_first_not_of(" \t\n\r");
  if (begin == std::string::npos) {
    return "";
  }
  const auto end = s.find_last_not_of(" \t\n\r");
  return s.substr(begin, end - begin + 1);
}
}  // namespace

std::string greeting(const std::string & name, int count)
{
  std::string who = trim(name);
  if (who.empty()) {
    who = "world";
  }
  return "hello " + who + " #" + std::to_string(count);
}
}  // namespace ros2_cpp_pkg
