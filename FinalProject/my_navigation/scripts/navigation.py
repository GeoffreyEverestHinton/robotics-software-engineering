#!/usr/bin/env python3
# move_base action导航客户端，传入x/y/角度(度)自动导航到地图目标点
import rospy,math,sys,actionlib
from geometry_msgs.msg import Pose,Point,Quaternion
from move_base_msgs.msg import MoveBaseAction,MoveBaseGoal
from tf.transformations import quaternion_from_euler

ACTION_MOVE_BASE = 'move_base'
FRAME_MAP = 'map'

class NavToPoint:
    def __init__(self):
        rospy.on_shutdown(self.clean_up)
        # 连接move_base动作服务器
        self.move_base = actionlib.SimpleActionClient(ACTION_MOVE_BASE,MoveBaseAction)
        rospy.loginfo('等待move_base服务...')
        self.move_base.wait_for_server(rospy.Duration(120))
        rospy.loginfo('已连接导航服务')
        self.move_base_running = False
        self.blocking = True
        rospy.sleep(1)

    def goto(self,target,blocking=True):
        # target=[x,y,yaw_deg] 发送导航目标
        self.blocking = blocking
        yaw = target[2] * math.pi / 180.0
        q = quaternion_from_euler(0,0,yaw)
        # 构造目标位姿
        target_pose = Pose(Point(target[0],target[1],0),Quaternion(q[0],q[1],q[2],q[3]))
        self.goal = MoveBaseGoal()
        self.goal.target_pose.header.frame_id = FRAME_MAP
        self.goal.target_pose.header.stamp = rospy.Time.now()
        self.goal.target_pose.pose = target_pose
        rospy.loginfo(f"前往 x:{target[0]} y:{target[1]} angle:{target[2]}°")
        rospy.sleep(1)
        self.move_base.send_goal(self.goal)
        self.move_base_running = True
        # 阻塞等待到达
        if blocking:
            self.move_base.wait_for_result()
            self.move_base_running = False
            state = self.move_base.get_state()
            if state == 3:
                rospy.loginfo("成功到达目标")
            else:
                rospy.logwarn(f"导航失败，状态码:{state}")

    def clean_up(self):
        # 节点退出取消所有导航目标
        if self.move_base_running:
            self.move_base.cancel_all_goals()
        rospy.loginfo("导航任务已终止")

if __name__ == '__main__':
    rospy.init_node('nav_to_point')
    nav = NavToPoint()
    # 读取命令行参数，无参数默认3m、0、90度
    if len(sys.argv)>=4:
        x,y,angle = float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3])
    else:
        x,y,angle = 3.0,0.0,90.0
    nav.goto([x,y,angle])