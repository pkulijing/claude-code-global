cmake_minimum_required(VERSION 3.16)
project(ros2_cpp_pkg)

# ament 优先：ament_cmake 最先 find、ament_package() 最后。
# CXX_FLAGS 规范：若确需设 CMAKE_CXX_FLAGS 必须追加 "${CMAKE_CXX_FLAGS}"，不可覆盖
# （覆盖会冲掉上游 / 工具链注入的 flag）。本骨架优先用 target_* 施加编译选项，避免全局污染，
# 故不直接写 CMAKE_CXX_FLAGS；告警走 add_compile_options。
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 依赖消费 步骤 2：find_package（步骤 1 = package.xml 已声明 <depend>）。
set(THIS_PACKAGE_INCLUDE_DEPENDS rclcpp std_msgs)
find_package(ament_cmake REQUIRED)
foreach(Dependency IN ITEMS ${THIS_PACKAGE_INCLUDE_DEPENDS})
  find_package(${Dependency} REQUIRED)
endforeach()

# 库：纯逻辑 greeter + 节点 TalkerNode。节点头公开包含 rclcpp，故 rclcpp / std_msgs 为 PUBLIC 依赖。
add_library(${PROJECT_NAME} SHARED
  src/greeter.cpp
  src/talker_node.cpp)
target_compile_features(${PROJECT_NAME} PUBLIC cxx_std_17)
target_include_directories(${PROJECT_NAME} PUBLIC
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  "$<INSTALL_INTERFACE:include/${PROJECT_NAME}>")
# 依赖消费 步骤 3：链接到目标。ament_target_dependencies 为 ROS/ament 包首选，自动附加
# include / link / definitions。
ament_target_dependencies(${PROJECT_NAME} PUBLIC ${THIS_PACKAGE_INCLUDE_DEPENDS})

# 可执行节点（薄 main 链接库）。
add_executable(talker src/main.cpp)
target_link_libraries(talker PRIVATE ${PROJECT_NAME})

# 安装路径约定：库 → lib/、可执行 → lib/<pkg>/、头 → include/<pkg>、launch → share/<pkg>/。
install(TARGETS ${PROJECT_NAME}
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin)
install(TARGETS talker
  RUNTIME DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/
  DESTINATION include/${PROJECT_NAME})
install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME})

# 导出（提供方）：下游链接本包 PUBLIC 接口时能找到导入目标与其传递依赖。
ament_export_targets(export_${PROJECT_NAME} HAS_LIBRARY_TARGET)
ament_export_dependencies(${THIS_PACKAGE_INCLUDE_DEPENDS})

# 测试：BUILD_TESTING 默认关（统一构建系统全局 BUILD_TESTING=0），用 -d BUILD_TESTING=ON 开。
if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_greeter test/test_greeter.cpp)
  target_link_libraries(test_greeter ${PROJECT_NAME})
endif()

ament_package()  # 必须最后且仅一次
