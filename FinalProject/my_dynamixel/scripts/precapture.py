#!/usr/bin/env python3
import rospy,math
from sensor_msgs.msg import JointState

current_joint_states={}
ANGLE_TOLERANCE=0.1#角度误差阈值rad

def joint_state_callback(msg):
    #刷新全局关节实时角度
    for n,p in zip(msg.name,msg.position):current_joint_states[n]=p

def wait_joint_reach_target(joint_name,target_pos,timeout=15.0):
    #等待关节到位，超时返回False
    t0=rospy.Time.now()
    r=rospy.Rate(50)
    while not rospy.is_shutdown():
        if (rospy.Time.now()-t0).to_sec()>timeout:
            rospy.logerr(f"{joint_name}超时，目标{target_pos:.4f} 当前{current_joint_states.get(joint_name)}")
            return False
        if joint_name not in current_joint_states:
            rospy.logwarn(f"无{joint_name}状态数据")
            r.sleep()
            continue
        err=abs(current_joint_states[joint_name]-target_pos)
        if err<ANGLE_TOLERANCE:
            rospy.loginfo(f"{joint_name}到位 目标{target_pos:.4f} 当前{current_joint_states[joint_name]:.4f} 误差{err:.4f}")
            return True
        r.sleep()

if __name__=='__main__':
    rospy.init_node('joint_target_init',anonymous=True)
    rospy.Subscriber('/joint_states',JointState,joint_state_callback)
    pub=rospy.Publisher('/command',JointState,queue_size=10)
    rospy.sleep(0.5)
    rospy.loginfo("按顺序调整舵机并校验到位")
    joint_targets=[('joint5',0.75932887247543782),('joint3',0.258639075188025),('joint4',-0.6979938779914944)]
    for jn,pos in joint_targets:
        pub.publish(JointState(name=[jn],position=[pos]))
        if not wait_joint_reach_target(jn,pos):
            rospy.logfatal("关节调整失败，退出程序")
            exit(1)
        rospy.sleep(0.2)
    rospy.loginfo("全部舵机调整校验完成")