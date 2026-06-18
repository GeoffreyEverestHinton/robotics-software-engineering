#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rospy
import os
from std_msgs.msg import String

LAUNCH_RUN = "roslaunch my_navigation all.launch &"
LAUNCH_STOP = "killall -9 roslaunch"

tts_pub = None
launch_running = False

def speak(text):
    tts_pub.publish(String(data=text))

def voice_callback(msg):
    global launch_running
    raw = msg.data
    # 1. 先过滤所有英文标点
    punctuation = ',./!?;:'
    for p in punctuation:
        raw = raw.replace(p, "")
    # 2. 只保留字母和空格
    clean_list = []
    for char in raw:
        if char.isalpha() or char == " ":
            clean_list.append(char)
    text = "".join(clean_list).strip().lower()

    rospy.loginfo("原始数据：%s", raw)
    rospy.loginfo("清洗后：%s", text)

    if ("start" in text or "here we go" in text) and not launch_running:
        os.system(LAUNCH_RUN)
        speak("here we go")
        launch_running = True
    elif "stop" in text or "come back" in text:
        os.system(LAUNCH_STOP)
        speak("ok here we stop")
        launch_running = False
    elif "hi lisa" in text:
        speak("I am here Doctor")

if __name__ == "__main__":
    rospy.init_node("voice_control_launch")
    rospy.Subscriber("/voice_words", String, voice_callback)
    tts_pub = rospy.Publisher("/voice_talk", String, queue_size=10)
    rospy.loginfo("语音控制节点启动完成")
    rospy.spin()

