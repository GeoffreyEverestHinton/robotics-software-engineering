# 机器人自主导航\&建图\&视觉检测\&机械臂配置使用手册
---

## 一、自主导航启动流程

机器人自主导航采用四层软硬件架构，需按顺序启动多终端节点，完成底盘驱动、激光数据转换、地图定位、可视化、自动任务启动全流程。

### 1\.1 终端启动步骤

#### 终端1：启动底盘驱动

```Plain Text
roslaunch turtlebot_bringup minimal.launch
```

#### 终端2：3D相机转激光Scan数据 \& 话题校验

```Plain Text
roslaunch turtlebot_bringup 3dsensor.launch
# 校验激光话题是否正常输出
rostopic hz /scan
```

#### 终端3：加载地图 \& AMCL定位

```Plain Text
roslaunch turtlebot_navigation amcl_demo.launch map_file:=/home/turing/catkin_ws/src/my_home_map.yaml
```

#### 终端4：RViz可视化配置启动

```Plain Text
rosrun rviz rviz -d ~/catkin_ws/src/my_navigation/rviz/my_map_config.rviz
```

#### 终端5：启动全自动导航任务状态机

```Plain Text
roslaunch my_navigation auto_nav.launch
```

#### 可选：查看机器人实时地图位姿

```Plain Text
rostopic echo /amcl_pose
```

### 1\.2 导航四层核心架构

1. **传感器层**：Kinect深度图通过`depthimage_to_laserscan`功能转换生成`/scan`激光数据；底盘硬件发布`/odom`里程计数据，为定位导航提供原始感知信息。

2. **AMCL定位层**：融合激光雷达数据、里程计数据与已知环境地图，通过粒子滤波算法实时解算机器人位姿，输出`/amcl_pose`定位结果。

3. **Move\_base导航层**：接收外部下发的导航目标点，通过全局路径规划\+局部动态避障规划，输出`/cmd_vel`速度控制指令。

4. **底盘控制层**：底盘节点订阅`/cmd_vel`速度话题，解析并执行运动指令，完成机器人前进、转向、调速等动作。

### 1\.3 整体导航运行流程

设备开机初始化 → 启动底盘驱动 → 启动激光感知数据转换 → 加载地图并启动定位导航 → 机器人位姿初始化校准 → 下发导航目标点 → 机器人自主规划路径行驶

---

## 二、GMapping SLAM建图流程

通过GMapping算法实现室内环境实时建图，配合键盘遥控遍历全屋，最终保存可用于导航的栅格地图文件。

### 2\.1 建图终端步骤

#### 终端1：启动底盘\+相机基础驱动

```Plain Text
source ~/catkin_ws/devel/setup.bash
roslaunch turtlebot_bringup minimal.launch
```

#### 终端2：启动GMapping SLAM建图节点

```Plain Text
source ~/catkin_ws/devel/setup.bash
roslaunch turtlebot_navigation gmapping_demo.launch
```

#### 终端3：键盘遥控机器人遍历建图

```Plain Text
source ~/catkin_ws/devel/setup.bash
roslaunch turtlebot_teleop keyboard_teleop.launch
```

### 2\.2 地图保存

低速遥控机器人全屋遍历，保证环境无死角扫描，建图完成后执行以下命令保存地图（生成 \.pgm 栅格地图文件 \+ \.yaml 配置文件）：

```Plain Text
rosrun map_server map_saver -f /home/turing/catkin_ws/src/my_home_map
```

### 2\.3 相机3D坐标说明

- **X轴**：相机左右偏移方向

- **Z轴**：相机前方距离方向

- **Y轴**：相机高度方向

⚠️ 注意：**相机像素坐标系与机器人基坐标系不通用**，视觉数据需通过坐标转换才可匹配机器人导航位姿。

---

## 三、YOLO视觉检测 \& Kinect相机驱动

集成Kinect深度相机RGB\-D感知与YOLO目标检测，实现环境图像采集、目标识别、视觉对位功能。

### 3\.1 YOLO环境配置

```Plain Text
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 3\.2 本地摄像头YOLO检测测试

```Plain Text
yolo predict model=yolov8n.pt source=0 show=True
```

### 3\.3 Kinect相机驱动启动

#### 基础驱动启动（带深度配准）

```Plain Text
roslaunch freenect_launch freenect.launch depth_registration:=true
# 校验图像话题是否正常发布
rostopic list | grep image_raw
```

#### RGB图 \& 深度图可视化

```Plain Text
# 可视化RGB图像
rosrun image_view image_view image:=/camera/rgb/image_raw
# 可视化深度图像
rosrun image_view image_view image:=/camera/depth/image_raw
```

#### RGB\-D对齐驱动启动

```Plain Text
roslaunch freenect_launch freenect-registered-xyzrgb.launch
```

### 3\.4 视觉自动对位脚本运行

```Plain Text
python3 ~/catkin_ws/src/my_navigation/scripts/mwy3.py
```

---


## 四、使用注意事项

1. 所有ROS节点需按文档顺序启动，避免传感器、定位、导航节点时序错乱导致功能异常。

2. 视觉导航需保证RGB\-D图像对齐正常，否则会出现坐标匹配偏差，影响对位精度。

3. 每次打开新终端，建议执行`source ~/catkin_ws/devel/setup.bash`加载环境变量。

