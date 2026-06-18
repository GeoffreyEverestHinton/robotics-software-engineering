cmake_minimum_required(VERSION 3.0.2)
project(my_dynamixel)

# 启用 C++11 标准（ROS通用）
add_compile_options(-std=c++11)

# 查找依赖包
find_package(catkin REQUIRED COMPONENTS
  dynamixel_workbench_controllers
  roscpp
  rospy
  std_msgs
)

# catkin 包导出配置
catkin_package(
  INCLUDE_DIRS include
  LIBRARIES ${PROJECT_NAME}
  CATKIN_DEPENDS dynamixel_workbench_controllers roscpp rospy std_msgs
)

# 头文件搜索路径
include_directories(
  include
  ${catkin_INCLUDE_DIRS}
)

# ====================== 编译库（可选）======================
add_library(${PROJECT_NAME}
  src/${PROJECT_NAME}/dynamixel_driver.cpp
)
add_dependencies(${PROJECT_NAME} ${catkin_EXPORTED_TARGETS})
target_link_libraries(${PROJECT_NAME} ${catkin_LIBRARIES})

# ====================== 编译C++可执行节点示例 ======================
# 舵机控制主节点
add_executable(dynamixel_control_node src/dynamixel_control_node.cpp)
add_dependencies(dynamixel_control_node ${catkin_EXPORTED_TARGETS})
target_link_libraries(dynamixel_control_node
  ${PROJECT_NAME}
  ${catkin_LIBRARIES}
)

# ====================== 安装配置 ======================
# 安装C++库
install(TARGETS ${PROJECT_NAME}
  ARCHIVE DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
  LIBRARY DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
  RUNTIME DESTINATION ${CATKIN_GLOBAL_BIN_DESTINATION}
)

# 安装可执行程序
install(TARGETS dynamixel_control_node
  RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# 安装头文件
install(DIRECTORY include/${PROJECT_NAME}/
  DESTINATION ${CATKIN_PACKAGE_INCLUDE_DESTINATION}
  FILES_MATCHING PATTERN "*.h"
  PATTERN ".svn" EXCLUDE
)

# 安装launch、urdf、参数文件等资源
install(DIRECTORY launch config urdf
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

# 安装Python脚本（如需）
# catkin_install_python(PROGRAMS
#   scripts/dynamixel_tune.py
#   DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
# )