# my\_dynamixel 机械臂舵机控制使用手册


## 一、硬件串口规则（重要固定规范）

### 1\.1 查看USB串口设备

查询当前系统USB串口设备：

```Plain Text
ls /dev/ttyUSB*
```

### 1\.2 串口固定规则

- 机械臂**固定插 ttyUSB0**，后续使用统一优先插入机械臂USB

- 串口序号特性：先插为 USB0，后插为 USB1

- 单独拔掉其中一个设备，剩余设备串口序号**不会刷新**

- 如需重置串口序号：**全部拔下重新插入**即可

## 二、机械臂关节对应表

|关节名称|舵机ID|机械结构位置|
|---|---|---|
|joint1|1|底座旋转关节|
|joint2|2|肩膀关节|
|joint3|3|肘部关节|
|joint4|4|腕部俯仰关节|
|joint5|5|末端夹爪关节|

**注意**：夹爪 joint5 控制逻辑与视觉左右逻辑相反，脚本逻辑正常，为硬件安装方向导致。

## 三、完整启动流程（多终端分步启动）

### 终端1：启动ROS核心（常驻）

```Plain Text
roscore
```

### 终端2：启动舵机控制器（常驻）

```Plain Text
source ~/catkin_ws/devel/setup.bash
roslaunch my_dynamixel ax12_controller.launch
```

### 终端3：发布舵机控制指令 / 读取状态

每次新开终端需先加载环境变量：

```Plain Text
source ~/catkin_ws/devel/setup.bash
```

## 四、舵机状态查看指令

读取当前机械臂所有关节角度（单次打印）：

```Plain Text
rostopic echo /joint_states -n 1
```

## 五、基础标准舵机控制指令（基础限位值）

### 5\.1 joint5 夹爪控制

最大张开：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint5'], position: [0.759]}"
```

完全夹紧：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint5'], position: [-0.622]}"
```

### 5\.2 joint4 腕部俯仰

向下垂直：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint4'], position: [1.9]}"
```

向上垂直：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint4'], position: [-1.9]}"
```

水平舒展归零：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint4'], position: [0.0]}"
```

### 5\.3 joint3 肘部控制

向下垂直：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint3'], position: [1.9]}"
```

舒展归零：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint3'], position: [0.0]}"
```

### 5\.4 joint2 肩部控制

向上限位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint2'], position: [-1.9]}"
```

原位舒展归零：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint2'], position: [0.0]}"
```

向下限位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint2'], position: [1.9]}"
```

### 5\.5 joint1 底座旋转

正左方归零：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint1'], position: [0.0]}"
```

## 六、实际调试精准点位指令（工程可用）

适配真机调试最优角度，替代基础限位值

### 6\.1 joint5 夹爪精准控制

最大张开：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint5'], position: [-0.6]}"
```

最小夹紧：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint5'], position: [0.3]}"
```

### 6\.2 joint4 腕部精准点位

最上限位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint4'], position: [-3.0]}"
```

最下限位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint4'], position: [0.2]}"
```

### 6\.3 joint3 肘部精准点位

最上限位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint3'], position: [-0.92]}"
```

最下限位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint3'], position: [2.8]}"
```

中间舒展位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint3'], position: [1.5]}"
```

### 6\.4 joint2 肩部精准点位

最上限位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint2'], position: [1.31]}"
```

最下限位：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint2'], position: [-1.31]}"
```

### 6\.5 joint1 底座精准旋转点位

正前方：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint1'], position: [-1.5]}"
```

正左方：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint1'], position: [-0.1]}"
```

正右方：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint1'], position: [0.3]}"
```

右前方：

```Plain Text
rostopic pub -1 /command sensor_msgs/JointState "{name: ['joint1'], position: [-2.4]}"
```

## 七、Python 功能脚本使用说明

### 7\.1 脚本路径

```Plain Text
cd ~/catkin_ws/src/my_dynamixel/scripts
```

### 7\.2 赋予脚本执行权限（首次必须执行）

```Plain Text
chmod +x /home/turing/catkin_ws/src/my_dynamixel/scripts/Fully.py
chmod +x /home/turing/catkin_ws/src/my_dynamixel/scripts/initialization.py
chmod +x /home/turing/catkin_ws/src/my_dynamixel/scripts/precapture.py
chmod +x /home/turing/catkin_ws/src/my_dynamixel/scripts/capture.py
chmod +x /home/turing/catkin_ws/src/my_dynamixel/scripts/laydown.py
```

### 7\.3 脚本运行命令

```Plain Text
# 全自动控制脚本
rosrun my_dynamixel scripts/Fully.py

# 机械臂初始化
rosrun my_dynamixel initialization.py

# 预抓取脚本
rosrun my_dynamixel precapture.py

# 抓取脚本
rosrun my_dynamixel capture.py

# 下放复位脚本
rosrun my_dynamixel laydown.py
```

## 八、关键注意事项

- ROS 环境下 Python 脚本**必须添加执行权限**才可被 rosrun 调用

- 所有控制指令发布话题为 **/command**，消息类型：**sensor\_msgs/JointState**

- 夹爪运动方向与视觉左右相反，属于硬件安装问题，脚本逻辑无误

- 启动顺序严格遵循：roscore → 控制器launch → 发布控制指令

- 新开终端务必执行 source 加载环境变量，否则找不到功能包

> （注：部分内容可能由 AI 生成）
