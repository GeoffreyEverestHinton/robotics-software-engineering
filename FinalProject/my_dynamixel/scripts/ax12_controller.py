#!/usr/bin/env python3
# AX-12A舵机ROS控制器 线程安全
import sys,time,math,rospy,threading
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from dynamixel_sdk import *
# 通信配置
PORT,BAUD,PROTO='/dev/ttyUSB0',1000000,1.0
JOINTS=['joint1','joint2','joint3','joint4','joint5']
class AX12Ctrl:
    def __init__(self):
        rospy.init_node('ax12_controller')
        self.port=PortHandler(PORT)
        # 串口初始化
        if not self.port.openPort() or not self.port.setBaudRate(BAUD):
            rospy.logfatal("串口打开失败");sys.exit(1)
        self.pkt=PacketHandler(PROTO)
        self.lock=threading.Lock()#串口操作互斥锁
        self.motors={}#存储在线舵机ID-关节名映射
        self.scan()#扫描在线舵机
        # ROS发布订阅
        self.pub=rospy.Publisher('joint_states',JointState,queue_size=10)
        rospy.Subscriber('command',JointState,self.on_cmd)
        rospy.Subscriber('joint_trajectory',JointTrajectory,self.on_traj)
        rospy.loginfo("控制器启动完成")
    def scan(self):
        ID_MAP={1:'joint1',2:'joint2',3:'joint3',4:'joint4',5:'joint5'}
        # 遍历1-25号舵机ping检测
        for mid in range(1,26):
            with self.lock:
                m,r,_=self.pkt.ping(self.port,mid)
                if r==0:
                    if mid in ID_MAP:self.motors[mid]=ID_MAP[mid];rospy.loginfo(f"ID{mid}绑定{ID_MAP[mid]}")
                    self.pkt.write1ByteTxRx(self.port,mid,24,1)#开启扭矩
                    time.sleep(0.02)
        if not self.motors:rospy.logfatal("未检测到舵机");sys.exit(1)
        rospy.loginfo(f"在线舵机数量:{len(self.motors)}")
    def raw2rad(self,r):#舵机原始值转弧度 0~1023→-150°~150°
        return (r/1023*300-150)*math.pi/180
    def rad2raw(self,r):#弧度转舵机原始位置值，限幅0-1023
        return max(0,min(1023,int((r/(math.pi*300/180)+150*math.pi/180/(math.pi*300/180))*1023)))
    def move(self,mid,raw):#平滑运动：低扭矩移动到位再升扭矩
        with self.lock:
            self.pkt.write1ByteTxRx(self.port,mid,24,1)#扭矩使能
            time.sleep(0.02)
            self.pkt.write2ByteTxRx(self.port,mid,34,400)#初始低扭矩
            time.sleep(0.05)
            self.pkt.write2ByteTxRx(self.port,mid,30,raw)#目标位置
            time.sleep(1.0)#运动等待时间
            # 阶梯提升扭矩
            for tl in [600,800,1023]:
                self.pkt.write2ByteTxRx(self.port,mid,34,tl)
                time.sleep(0.5)
            return True
    def on_cmd(self,msg):#JointState指令回调
        if not msg.name or not msg.position:return
        rospy.loginfo(f"接收指令:{msg.name} {[f'{p:.2f}' for p in msg.position]}")
        for i,name in enumerate(msg.name):
            for mid,jname in self.motors.items():
                if jname==name and i<len(msg.position):
                    raw=self.rad2raw(msg.position[i])
                    ok=self.move(mid,raw)
                    rospy.loginfo(f"{name}(ID{mid}) raw:{raw} {'成功'if ok else '失败'}")
    def on_traj(self,msg):#轨迹指令回调，取第一个点位执行
        if msg.points:self.on_cmd(JointState(name=msg.joint_names,position=msg.points[0].positions))
    def run(self):#主循环，20Hz发布关节状态，定时校验扭矩
        r=rospy.Rate(20)
        check=0
        while not rospy.is_shutdown():
            check+=1
            if check>=50:#每50帧校验一次扭矩开关
                check=0
                with self.lock:
                    for mid in self.motors:
                        tq,_,_=self.pkt.read1ByteTxRx(self.port,mid,24)
                        if tq!=1:
                            self.pkt.write1ByteTxRx(self.port,mid,24,1)
                            rospy.logwarn(f"ID{mid}扭矩丢失，重新开启")
            # 组装并发布关节状态
            js=JointState(header=rospy.Header(stamp=rospy.Time.now()))
            with self.lock:
                for mid in [1,2,3,4,5]:
                    name=self.motors.get(mid)
                    if not name:continue
                    p,rr,_=self.pkt.read2ByteTxRx(self.port,mid,36)
                    if rr==0:
                        js.name.append(name);js.position.append(self.raw2rad(p))
                        js.velocity.append(0);js.effort.append(0)
                    else:
                        js.name.append(name);js.position.append(0.0)
                        js.velocity.append(0);js.effort.append(0)
            self.pub.publish(js);r.sleep()
        self.port.closePort()#退出关闭串口
if __name__=='__main__':
    AX12Ctrl().run()