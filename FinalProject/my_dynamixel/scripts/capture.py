#!/usr/bin/env python3
import rospy,math
from sensor_msgs.msg import JointState

current_joint_states={}
POSITION_TOLERANCE=0.05#到位误差阈值(rad)

def joint_state_callback(msg):
    #更新各关节实时位置
    for n,p in zip(msg.name,msg.position):current_joint_states[n]=p

def wait_joint_reach_target(joint_name,target_pos,timeout=5.0):
    #等待关节走到目标，超时抛异常
    t0=rospy.Time.now().to_sec()
    r=rospy.Rate(50)
    while not rospy.is_shutdown():
        if rospy.Time.now().to_sec()-t0>timeout:raise TimeoutError(f"{joint_name}超时未到位({timeout}s)")
        if joint_name not in current_joint_states:
            rospy.logwarn(f"无{joint_name}状态数据")
            r.sleep()
            continue
        err=abs(current_joint_states[joint_name]-target_pos)
        if err<POSITION_TOLERANCE:
            rospy.loginfo(f"{joint_name}到位，目标{target_pos:.4f} 当前{current_joint_states[joint_name]:.4f} 误差{err:.4f}")
            break
        rospy.logdebug(f"{joint_name}未到位，误差{err:.4f}")
        r.sleep()

if __name__=='__main__':
    try:
        rospy.init_node('joint_adjust',anonymous=True)
        rospy.Subscriber("/joint_states",JointState,joint_state_callback)
        pub=rospy.Publisher('/command',JointState,queue_size=10)
        rospy.sleep(0.5)
        rospy.loginfo("开始调节舵机")
        #发送joint5目标位置
        cmd=JointState()
        cmd.name=['joint5']
        cmd.position=[-0.2]
        pub.publish(cmd)
        wait_joint_reach_target('joint5',-0.2)
        rospy.loginfo("全部调节完成")
    except rospy.ROSInterruptException:rospy.logerr("ROS中断")
    except TimeoutError as e:rospy.logerr(e)
    except Exception as e:rospy.logerr(f"异常:{e}")