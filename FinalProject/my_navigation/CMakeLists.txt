cmake_minimum_required(VERSION 3.0.2)
project(my_navigation)

# 依赖包
find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  nav_msgs
  rospy
  std_msgs
  roscpp
  sensor_msgs
  cv_bridge
  ultralytics # 若YOLO相关需要，无则可删
  move_base_msgs
  tf
)

# 导出依赖
catkin_package(
  CATKIN_DEPENDS
    geometry_msgs
    nav_msgs
    rospy
    std_msgs
    roscpp
    sensor_msgs
    cv_bridge
    move_base_msgs
    tf
)

# 头文件目录
include_directories(
  ${catkin_INCLUDE_DIRS}
  /usr/include/eigen3
)

# 安装所有python可执行脚本
catkin_install_python(PROGRAMS
  scripts/nav_action_client.py
  scripts/p.py
  scripts/water_cup_detector.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# 安装launch、config、rviz资源文件
install(DIRECTORY launch config rviz
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)