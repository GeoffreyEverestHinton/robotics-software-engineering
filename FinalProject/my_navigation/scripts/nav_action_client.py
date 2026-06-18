#!/usr/bin/env python3
# move_base导航Action客户端，bash调用，返回0成功/1失败
import sys,rospy,actionlib
from move_base_msgs.msg import MoveBaseAction,MoveBaseGoal

def nav_to_target(x,y,oz,ow,timeout=240):
    rospy.init_node("nav_action_client_node",anonymous=True)
    client=actionlib.SimpleActionClient("move_base",MoveBaseAction)
    rospy.loginfo("等待move_base服务")
    if not client.wait_for_server(rospy.Duration(10.0)):
        rospy.logerr("move_base未启动")
        return 1
    # 构造map坐标系导航目标
    goal=MoveBaseGoal()
    goal.target_pose.header.frame_id="map"
    goal.target_pose.header.stamp=rospy.Time.now()
    goal.target_pose.pose.position.x=float(x)
    goal.target_pose.pose.position.y=float(y)
    goal.target_pose.pose.position.z=0.0
    goal.target_pose.pose.orientation.x=0.0
    goal.target_pose.pose.orientation.y=0.0
    goal.target_pose.pose.orientation.z=float(oz)
    goal.target_pose.pose.orientation.w=float(ow)
    client.send_goal(goal)
    rospy.loginfo("已下发导航目标")
    # 阻塞等待结果
    finished=client.wait_for_result(rospy.Duration(timeout))
    state=client.get_state()
    if not finished:
        rospy.logerr(f"导航超时{timeout}s")
        return 1
    # 状态3=成功抵达
    if state==3:
        rospy.loginfo("导航到达目标")
        return 0
    else:
        rospy.logerr(f"导航失败，状态码{state}")
        return 1

if __name__=="__main__":
    # 校验输入参数：必须x y oz ow四个值
    if len(sys.argv)!=5:
        print("用法: python3 nav_action_client.py x y oz ow")
        sys.exit(1)
    x,y,oz,ow=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
    ret=nav_to_target(x,y,oz,ow)
    sys.exit(ret)