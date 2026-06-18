cmake_minimum_required(VERSION 2.8.3)
project(robot_voice)

# 启用 C++11
add_compile_options(-std=c++11)

# 1. 查找ROS依赖
find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
)

# 2. 查找ALSA音频系统库（录音linuxrec.c必需）
find_package(ALSA REQUIRED)

# 3. catkin包导出配置
catkin_package(
  INCLUDE_DIRS include ${ALSA_INCLUDE_DIRS}
  CATKIN_DEPENDS roscpp rospy std_msgs
  DEPENDS ALSA
)

# 头文件目录
include_directories(
  include
  ${catkin_INCLUDE_DIRS}
  ${ALSA_INCLUDE_DIRS}
)

# 自动判断系统架构，加载讯飞msc库(x64/x86)
EXECUTE_PROCESS( COMMAND uname -m COMMAND tr -d '\n' OUTPUT_VARIABLE ARCHITECTURE )
message(STATUS "System Architecture: ${ARCHITECTURE}")
if (${ARCHITECTURE} MATCHES "64")
  link_directories(${catkin_LIB_DIRS} libs/x64)
else()
  link_directories(${catkin_LIB_DIRS} libs/x86)
endif()

# ====================== 编译三个C++可执行节点 ======================
# TTS语音合成节点
add_executable(tts_subscribe src/tts_subscribe.cpp)
add_dependencies(tts_subscribe ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
target_link_libraries(
  tts_subscribe
  ${catkin_LIBRARIES}
  libmsc.so -ldl -pthread
)

# IAT语音识别节点（包含ALSA录音linuxrec.c）
add_executable(iat_publish src/iat_publish.cpp src/speech_recognizer.c src/linuxrec.c)
add_dependencies(iat_publish ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
target_link_libraries(
  iat_publish
  ${catkin_LIBRARIES}
  libmsc.so -ldl -lpthread -lm -lrt ${ALSA_LIBRARIES}
)

# 语音总控节点 voice_control
add_executable(voice_control src/voice_control.cpp)
add_dependencies(voice_control ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
target_link_libraries(
  voice_control
  ${catkin_LIBRARIES}
  libmsc.so -ldl -pthread
)

# ====================== 安装配置 ======================
# 安装C++可执行程序
install(TARGETS tts_subscribe iat_publish voice_control
  RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# 安装Python指令解析脚本 voice_cmd.py
catkin_install_python(PROGRAMS
  scripts/voice_cmd.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# 安装头文件
install(DIRECTORY include/
  DESTINATION ${CATKIN_PACKAGE_INCLUDE_DESTINATION}
  FILES_MATCHING PATTERN "*.h"
)

# 安装讯飞静态库、launch启动文件
install(DIRECTORY libs launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)