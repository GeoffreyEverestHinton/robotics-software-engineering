#!/usr/bin/env python3
import rospy,math
from sensor_msgs.msg import JointState

current_joint_states={}
POSITION_TOLERANCE=0.05#到位误差阈值(rad)

def joint_state_callback(msg):
    #更新全局关节实时位置
    for n,p in zip(msg.name,msg.position):current_joint_states[n]=p

def wait_joint_reach_target(joint_name,target_pos,timeout=15.0):
    #阻塞等待关节到位，超时抛异常
    t0=rospy.Time.now()
    r=rospy.Rate(50)
    while not rospy.is_shutdown():
        if (rospy.Time.now()-t0).to_sec()>timeout:raise TimeoutError(f"{joint_name}{timeout}s未到位")
        if joint_name not in current_joint_states:
            rospy.logwarn(f"无{joint_name}状态反馈")
            r.sleep()
            continue
        err=abs(current_joint_states[joint_name]-target_pos)
        if err<POSITION_TOLERANCE:
            rospy.loginfo(f"{joint_name}到位 目标{target_pos:.2f} 当前{current_joint_states[joint_name]:.2f} 误差{err:.3f}")
            break
        rospy.logdebug(f"{joint_name}未到位 误差{err:.3f}")
        r.sleep()

if __name__=='__main__':
    try:
        rospy.init_node('joint_move',anonymous=True)
        rospy.Subscriber("/joint_states",JointState,joint_state_callback)
        pub=rospy.Publisher('/command',JointState,queue_size=10)
        rospy.sleep(0.5)
        rospy.loginfo("开始调节舵机")
        #joint3运动
        pub.publish(JointState(name=['joint3'],position=[0.25]))
        wait_joint_reach_target('joint3',0.25)
        #joint5运动
        pub.publish(JointState(name=['joint5'],position=[0.769]))
        wait_joint_reach_target('joint5',0.769)
        rospy.loginfo("全部舵机调节完成")
    except rospy.ROSInterruptException:rospy.logerr("ROS中断")
    except TimeoutError as e:rospy.logerr(e)
    except Exception as e:rospy.logerr(f"异常:{e}")