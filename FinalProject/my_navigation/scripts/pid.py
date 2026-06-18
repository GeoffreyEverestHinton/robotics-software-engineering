#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# YOLO水杯检测+PID视觉循迹自动靠近机器人程序
import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from ultralytics import YOLO
import time
from geometry_msgs.msg import Twist

# PID控制器类：实现位置闭环调速
class PIDController:
    def __init__(self, kp, ki, kd, min_output, max_output):
        self.kp = kp                # 比例系数
        self.ki = ki                # 积分系数
        self.kd = kd                # 微分系数
        self.min_output = min_output# 输出下限
        self.max_output = max_output# 输出上限
        self.last_error = 0.0       # 上一次误差
        self.integral = 0.0         # 积分累加值
        self.last_time = time.time()# 上次计算时间戳

    def compute(self, error):
        """输入误差，输出PID控制量"""
        current_time = time.time()
        dt = current_time - self.last_time
        if dt < 1e-6: # 防止时间差过小除零
            return 0.0
        # 比例项
        p_term = self.kp * error
        # 积分项，限幅防积分饱和
        self.integral += error * dt
        integral_limit = self.max_output / self.ki if self.ki != 0 else 0
        self.integral = np.clip(self.integral, -integral_limit, integral_limit)
        i_term = self.ki * self.integral
        # 微分项
        derivative = (error - self.last_error) / dt
        d_term = self.kd * derivative
        # 合并输出并限幅
        output = p_term + i_term + d_term
        output = np.clip(output, self.min_output, self.max_output)
        # 更新缓存
        self.last_error = error
        self.last_time = current_time
        return output

    def reset(self):
        """清空PID累计状态"""
        self.last_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()

# 水杯检测追踪主类
class WaterCupDetector:
    def __init__(self):
        rospy.init_node('water_cup_detector_node', anonymous=True)
        self.last_detect_time = 0               # 上一次检测时间戳，控制检测帧率
        self.model = YOLO("yolov8n.pt")         # 加载YOLO模型
        self.model.to("cpu")
        self.bridge = CvBridge()               # ROS图像与OpenCV转换工具
        # 订阅RGB彩色图、深度图话题
        self.image_sub = rospy.Subscriber("/camera/rgb/image_raw", Image, self.image_callback)
        self.depth_sub = rospy.Subscriber("/camera/depth_registered/image_raw", Image, self.depth_callback)
        self.target_class = 39                  # YOLO类别39=水杯
        self.depth_image = None                 # 缓存深度图
        self.cmd_vel_pub = rospy.Publisher('/mobile_base/commands/velocity', Twist, queue_size=10) # 底盘速度发布

        # 图像与对准参数
        self.image_center_x = 320
        self.image_center_y = 240
        self.align_tolerance_pixel = 10         # 水平对准像素误差阈值
        self.distance_tolerance_m = 0.06        # 目标距离误差阈值(m)
        self.max_angular_speed = 0.45           # 最大角速度
        self.max_linear_speed = 0.22            # 最大线速度
        self.min_angular_speed = 0.12           # 最小角速度(防止动不起来)
        self.min_linear_speed = 0.07            # 最小线速度
        self.target_z = 0.6                     # 目标停靠距离(m)

        # PID实例：水平转向PID、前进距离PID
        self.angular_pid = PIDController(kp=0.008, ki=0.001, kd=0.0005, min_output=-self.max_angular_speed, max_output=self.max_angular_speed)
        self.linear_pid = PIDController(kp=0.9, ki=0.1, kd=0.05, min_output=-self.max_linear_speed, max_output=self.max_linear_speed)

        # 到达目标后流程参数
        self.reach_target = False               # 是否到达目标距离
        self.target_reached_time = 0            # 到达目标时刻
        self.wait_duration = 2.0                # 到位后等待时长
        self.move_forward_distance = 0.35      # 等待后继续前进距离
        self.move_forward_speed = 0.08         # 前进速度
        self.move_forward_start_time = 0
        self.move_forward_finished = False
        self.program_finished = False           # 程序总结束标志

        # 丢失目标自动搜寻参数
        self.no_target_start_time = time.time() # 丢失目标起始时间
        self.lost_target_timeout = 4.0          # 丢失多久后开始旋转搜寻
        self.rotate_angle_per_time = 90.0       # 单次搜寻旋转角度
        self.total_rotate_limit = 720.0         # 累计旋转上限，超了直接退出
        self.total_rotated_angle = 0.0          # 累计旋转总角度
        self.rotate_vel = 0.4                  # 搜寻旋转速度
        self.is_rotating = False               # 是否正在搜寻旋转
        self.rotate_start_time = 0.0

        # 目标记忆：记录上次有效目标位置，用于丢失后定向搜寻
        self.last_valid_cx = None
        self.had_target_before = False

        rospy.loginfo("✅ 双退出逻辑：1.转满720°退出  2.到达目标位置退出")
        rospy.loginfo("🔧 已启用PID控制模式")

    def depth_callback(self, msg):
        """深度图像订阅回调，缓存深度图"""
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except CvBridgeError as e:
            rospy.logerr(f"深度图转换失败: {e}")

    def stop_all_move(self):
        """发布零速度，小车停止"""
        twist = Twist()
        self.cmd_vel_pub.publish(twist)

    def image_callback(self, msg):
        """RGB图像主回调：检测目标、PID控速、搜寻、后置前进逻辑"""
        if self.program_finished:
            return
        # ROS图像转OpenCV
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            h, w = cv_image.shape[:2]
            self.image_center_x = w // 2
            self.image_center_y = h // 2
        except Exception as e:
            return
        # 控制检测频率，避免算力占用过高
        current_time = time.time()
        if current_time - self.last_detect_time < 0.18:
            return
        self.last_detect_time = current_time

        frame = cv_image.copy()
        target_found = False
        cx, cy, z = 0, 0, 0

        # 分支1：正在执行搜寻旋转
        if self.is_rotating:
            twist = Twist()
            rad = np.pi / 180.0
            dur = (self.rotate_angle_per_time * rad) / abs(self.rotate_vel)
            # 旋转计时未结束，持续转向
            if current_time - self.rotate_start_time < dur:
                twist.angular.z = self.rotate_vel
                self.cmd_vel_pub.publish(twist)
                cv2.imshow("Detect", frame)
                cv2.waitKey(1)
                return
            # 单次旋转完成
            else:
                self.is_rotating = False
                self.total_rotated_angle += self.rotate_angle_per_time
                rospy.loginfo(f"🔁 单次旋转完成，累计 {self.total_rotated_angle}°")
                # 累计旋转超限，任务终止
                if self.total_rotated_angle >= self.total_rotate_limit:
                    rospy.logwarn("❌ 累计旋转720°未找到目标，程序退出")
                    self.stop_all_move()
                    self.program_finished = True
                    cv2.destroyAllWindows()
                    rospy.signal_shutdown("搜寻超时退出")
                    return
                self.no_target_start_time = current_time

        # 分支2：YOLO目标检测，提取水杯框中心与深度
        results = self.model(cv_image, verbose=False)
        frame = results[0].plot()
        if len(results[0].boxes) > 0:
            for box in results[0].boxes:
                if int(box.cls) == self.target_class:
                    target_found = True
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    # 获取目标平均深度
                    if self.depth_image is not None:
                        depth = self.get_depth1(x1, y1, x2, y2)
                        if depth > 0:
                            _, _, z = self.pixel_to_3d(cx, cy, depth)
                    self.last_valid_cx = cx
                    self.had_target_before = True
                    break

        # 分支3：检测到水杯，PID闭环控制对准+靠近
        if target_found:
            self.no_target_start_time = current_time
            self.total_rotated_angle = 0.0
            if not self.reach_target:
                twist = Twist()
                pixel_offset = self.image_center_x - cx
                # 水平角度PID调节
                if abs(pixel_offset) > self.align_tolerance_pixel:
                    angular_speed = self.angular_pid.compute(pixel_offset)
                    # 最低转速限制
                    if abs(angular_speed) < self.min_angular_speed:
                        angular_speed = self.min_angular_speed if angular_speed > 0 else -self.min_angular_speed
                    twist.angular.z = angular_speed
                else:
                    twist.angular.z = 0
                    self.angular_pid.reset()
                    # 距离PID调节前进后退
                    if z > 0:
                        distance_offset = z - self.target_z
                        if abs(distance_offset) > self.distance_tolerance_m:
                            linear_speed = self.linear_pid.compute(distance_offset)
                            if abs(linear_speed) < self.min_linear_speed:
                                linear_speed = self.min_linear_speed if linear_speed > 0 else -self.min_linear_speed
                            twist.linear.x = linear_speed
                        else:
                            twist.linear.x = 0
                            self.linear_pid.reset()
                            self.reach_target = True
                            self.target_reached_time = current_time
                            rospy.loginfo("✅ 已到达目标距离，准备等待后前进")
                self.cmd_vel_pub.publish(twist)

        # 分支4：丢失目标，停止运动，超时后启动搜寻旋转
        else:
            twist = Twist()
            twist.linear.x = 0
            twist.angular.z = 0
            self.cmd_vel_pub.publish(twist)
            # 丢失目标重置PID
            self.angular_pid.reset()
            self.linear_pid.reset()
            lost_dur = current_time - self.no_target_start_time
            rospy.logwarn(f"⚠️ 丢失目标 {lost_dur:.1f}s / {self.lost_target_timeout}s")
            # 超时进入搜寻模式
            if lost_dur >= self.lost_target_timeout:
                rospy.loginfo("⏰ 丢失超时，开始转向搜寻")
                self.is_rotating = True
                self.rotate_start_time = current_time
                # 根据上次目标位置选择旋转方向
                if not self.had_target_before or self.last_valid_cx is None:
                    self.rotate_vel = abs(self.rotate_vel)
                    rospy.loginfo("🔍 从未检测到目标，顺时针旋转")
                else:
                    if self.last_valid_cx < self.image_center_x:
                        self.rotate_vel = abs(self.rotate_vel)
                        rospy.loginfo("↩️ 目标最后在左侧，逆时针旋转")
                    else:
                        self.rotate_vel = -abs(self.rotate_vel)
                        rospy.loginfo("↪️ 目标最后在右侧，顺时针旋转")

        # 分支5：成功抵达目标后，等待一段时间再向前行驶一段距离
        if self.reach_target:
            twist = Twist()
            if not self.move_forward_finished and current_time - self.target_reached_time < self.wait_duration:
                twist.linear.x = 0
                rospy.loginfo(f"⏳ 等待中，剩余 {self.wait_duration - (current_time - self.target_reached_time):.1f}s")
            elif not self.move_forward_finished:
                if self.move_forward_start_time == 0:
                    self.move_forward_start_time = current_time
                req_time = self.move_forward_distance / self.move_forward_speed
                elapsed = current_time - self.move_forward_start_time
                if elapsed < req_time:
                    twist.linear.x = self.move_forward_speed
                    rospy.loginfo(f"🛣️ 前进中：{elapsed * self.move_forward_speed * 100:.1f}cm/{self.move_forward_distance * 100}cm")
                else:
                    twist.linear.x = 0
                    self.move_forward_finished = True
                    rospy.loginfo("🏁 前进动作完成")
            else:
                # 整套流程完成，程序退出
                rospy.loginfo("🎉 成功到达目标位置，程序退出")
                self.stop_all_move()
                self.program_finished = True
                cv2.destroyAllWindows()
                rospy.signal_shutdown("任务完成退出")
            self.cmd_vel_pub.publish(twist)

        # 可视化窗口刷新
        cv2.imshow("Detect", frame)
        cv2.waitKey(1)

    def get_depth1(self, x1, y1, x2, y2):
        """截取目标框ROI，过滤异常值后计算平均深度"""
        if self.depth_image is None:
            return -1
        h, w = self.depth_image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        roi = self.depth_image[y1:y2, x1:x2]
        sorted_roi = np.sort(roi.flatten())
        keep_num = int(len(sorted_roi) * 0.75)
        valid_depth = sorted_roi[:keep_num][sorted_roi[:keep_num] > 0]
        if valid_depth.size == 0:
            return -1
        avg_depth = np.mean(valid_depth)
        # 深度单位转换 mm→m
        if self.depth_image.dtype == np.uint16:
            avg_depth /= 1000.0
        return avg_depth if 0.05 < avg_depth < 10 else -1

    def pixel_to_3d(self, cx, cy, depth):
        """像素坐标+深度转相机三维坐标"""
        fx = fy = 554.387 # 相机内参焦距
        x = (cx - self.image_center_x) * depth / fx
        y = (cy - self.image_center_y) * depth / fy
        return x, y, depth

if __name__ == '__main__':
    try:
        detector = WaterCupDetector()
        rospy.spin() # ROS消息循环阻塞
    except rospy.ROSInterruptException:
        pass
    finally:
        # 程序退出兜底：停车、关闭窗口
        twist = Twist()
        detector.cmd_vel_pub.publish(twist)
        cv2.destroyAllWindows()