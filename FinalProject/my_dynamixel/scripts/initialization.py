#!/usr/bin/env python3
import rospy
from std_msgs.msg import Bool
from sensor_msgs.msg import JointState

def is_joint_reached(target_joint, target_pos, tolerance=0.01):
    # 临时订阅获取单关节实时位置，3s超时判断是否到位
    current_pos = None
    def joint_state_cb(msg):
        nonlocal current_pos
        if target_joint in msg.name:
            current_pos = msg.position[msg.name.index(target_joint)]
    sub = rospy.Subscriber('/joint_states', JointState, joint_state_cb)
    timeout = rospy.Time.now() + rospy.Duration(3.0)
    while rospy.Time.now() < timeout and current_pos is None: rospy.sleep(0.01)
    sub.unregister()
    if current_pos is None:
        rospy.logerr(f"无{target_joint}状态反馈")
        return False
    return abs(current_pos - target_pos) < tolerance

if __name__ == '__main__':
    rospy.init_node('joint_fast_init', anonymous=True)
    pub = rospy.Publisher('/command', JointState, queue_size=10)
    rospy.sleep(0.5)
    rospy.loginfo("按5→4→3→2→1顺序复位舵机")
    # 各关节目标弧度
    joint_targets = [('joint5',0.14799944345377252),('joint4',1.7628983784683383),('joint3',-2.4488800627601601),('joint2',2.11330871010124),('joint1',-1.5506413013729362)]
    for jn,pos in joint_targets:
        pub.publish(JointState(name=[jn],position=[pos]))
        rospy.loginfo(f"等待{jn}到位")
        if is_joint_reached(jn,pos): rospy.loginfo(f"{jn}已到位")
        else: rospy.logwarn(f"{jn}未到位，继续执行")
    # 标记初始化完成
    rospy.set_param('/arm_init_complete', True)
    complete_pub = rospy.Publisher('/arm_init_complete', Bool, queue_size=10)
    complete_pub.publish(True)
    rospy.loginfo("全部舵机复位完成")