#!/usr/bin/env python3
# ROS摄像头YOLO目标检测节点
import rospy
import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge  # ROS图像与OpenCV图像转换工具
from ultralytics import YOLO     # YOLO目标检测库

bridge = CvBridge()             # 实例化图像转换工具
model = YOLO("../yolov8n.pt")   # 加载YOLOv8n本地权重文件

# 相机图像订阅回调函数
def image_callback(msg):
    # ROS图像消息转为OpenCV BGR图像
    frame = bridge.imgmsg_to_cv2(msg, "bgr8")
    # 执行YOLO目标检测推理
    results = model(frame)
    # 在原图上绘制检测框、类别、置信度
    frame_result = results[0].plot()
    # 弹出窗口展示检测画面
    cv2.imshow("ROBOT CAMERA + YOLO", frame_result)
    cv2.waitKey(1)  # 刷新图像窗口

if __name__ == "__main__":
    rospy.init_node("yolo_node")
    # 订阅深度相机RGB图像话题
    rospy.Subscriber("/camera/rgb/image_raw", Image, image_callback)
    rospy.spin()  # 持续监听ROS消息回调
    cv2.destroyAllWindows()  # 程序结束销毁OpenCV窗口