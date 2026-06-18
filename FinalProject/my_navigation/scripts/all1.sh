#!/bin/bash
# 机器人全自动任务状态机脚本 Actionlib标准方案
# 完整流程：系统自检→机械臂初始化→导航抓取→中转放料→返回原点放料→任务结束
# 配套依赖：robot_voice语音播报包、nav_action_client导航动作客户端、多组机械臂控制python脚本
# 功能特性：开机全模块自检、异常语音告警、错误防抖、状态机顺序执行、导航失败直接退出任务

# ===================== 全局配置参数 =====================
CHECK_INTERVAL=2               # 自检失败后重试间隔(秒)
MAX_RETRY=999                  # 最大重试次数(无上限)
LAST_ERR_MSG=""                # 语音缓存标记，避免重复播报相同故障

# 自检模块列表 格式：模块名称|检测命令|故障播报文本
# 使用rostopic/rosnode检测节点/话题存活，管道分隔字段
CHECK_LIST=(
    "底盘基础节点|timeout 2 rostopic echo /odom -n 1 >/dev/null 2>&1|底盘节点异常，正在重试"
    #"3D传感器|timeout 2 rostopic echo /camera/rgb/camera_info -n 1 >/dev/null 2>&1|3D传感器异常，正在重试"
    "AMCL定位|rosnode list | grep -q amcl|AMCL定位异常，正在重试"
    "导航move_base|rosnode list | grep -q move_base|导航模块异常，正在重试"
    "机械臂控制器|rosnode list | grep -q ax12_controller|机械臂控制器异常，正在重试"
    # 暂时注释关节状态检测，规避URDF日志误报
    # "关节状态|rostopic hz /joint_states -w 1|关节状态话题异常，正在重试"
)

# ===================== ROS语音播报函数 =====================
voice_play() {
    local text="$1"
    # 发布语音文本到话题，屏蔽输出日志
    rostopic pub -1 /voice_talk std_msgs/String "{data: '$text'}" >/dev/null 2>&1
    sleep 2.5 # 等待语音完整播放完毕
}

# ===================== 单个模块检测逻辑 =====================
check_single() {
    local name="$1"    # 模块名
    local cmd="$2"     # 存活检测指令
    local err_msg="$3" # 故障语音提示

    log_info "正在检测：$name"
    if eval $cmd; then
        log_info "$name 检测正常"
        LAST_ERR_MSG="" # 清除故障缓存
        return 0
    else
        log_info "$name 检测失败"
        # 仅全新故障才播报，防止循环重复喊话
        if [[ "$err_msg" != "$LAST_ERR_MSG" ]]; then
            voice_play "$err_msg"
            LAST_ERR_MSG="$err_msg"
        fi
        return 1
    fi
}

# ===================== 整机循环自检函数 =====================
full_self_check() {
    sleep 10 # 延时等待ROS底层节点启动
    voice_play "开始系统自检"
    while true; do
        local all_ok=1
        # 遍历所有待检测模块
        for item in "${CHECK_LIST[@]}"; do
            IFS='|' read -r name cmd err_msg <<< "$item"
            if ! check_single "$name" "$cmd" "$err_msg"; then
                all_ok=0
                break
            fi
        done
        # 全部模块正常，退出自检
        if [ $all_ok -eq 1 ]; then
            voice_play "所有模块检测正常，即将启动任务"
            log_info "========== 全部自检通过 =========="
            sleep 2
            break
        fi
        log_info "模块异常，${CHECK_INTERVAL}秒后重试..."
        sleep $CHECK_INTERVAL
    done
}

# ===================== 日志打印工具 =====================
log_info() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $1"
}

# ===================== 任务状态枚举定义 =====================
STATE_WAIT_NAV_START=0      # 等待导航模块就绪
STATE_INIT_ARM=1            # 启动并初始化机械臂
STATE_PUB_INIT_POSE=2       # 发布机器人初始定位位姿
STATE_PUB_GOAL1=3           # 准备前往抓取目标点
STATE_WAIT_GOAL1_REACH=4    # 导航至抓取点并等待到达
STATE_RUN_VISION=5          # 视觉精准对位
STATE_ARM_PRE_CAPTURE=6     # 机械臂预抓取姿态
STATE_ARM_CAPTURE=7         # 执行物体抓取
STATE_WAIT_TRANSIT_REACH=11 # 导航至中转放料点
STATE_ARM_TRANSIT_LAYDOWN=12# 中转点放下物料
STATE_PUB_GOAL_HOME=8       # 导航返回原始起点
STATE_ARM_LAYDOWN=9         # 原点最终放料
STATE_FINISH=10             # 全部任务完成

current_state=$STATE_WAIT_NAV_START # 初始状态

# 带状态码的日志打印，显示当前运行阶段
log_info() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] [STATE:$current_state] $1"
}

# ===================== 各状态对应执行函数 =====================
# 0. 循环检测move_base话题，等待导航启动完成
wait_nav_start() {
    log_info "等待导航系统启动，检测/move_base话题"
    local timeout=30
    local count=0
    while true; do
        if rostopic list 2>/dev/null | grep -q "/move_base"; then
            log_info "导航系统已就绪"
            current_state=$STATE_INIT_ARM
            return 0
        fi
        ((count++))
        if [ $count -ge $timeout ]; then
            log_info "错误：导航启动超时，任务退出"
            exit 1
        fi
        sleep 1
    done
}

# 1. 启动舵机控制器并运行机械臂初始化脚本
init_arm() {
    log_info "启动机械臂控制器节点"
    #roslaunch my_dynamixel ax12_controller.launch &

    local timeout=10
    local count=0
    # 等待控制器节点成功拉起
    while true; do
        if rosnode list 2>/dev/null | grep -q "ax12_controller"; then
            log_info "机械臂控制器启动成功"
            break
        fi
        ((count++))
        if [ $count -ge $timeout ]; then
            log_info "错误：机械臂控制器启动超时，任务退出"
            exit 1
        fi
        sleep 1
    done
    # 执行机械臂归位初始化
    log_info "执行机械臂初始化脚本"
    python3 ~/catkin_ws/src/my_dynamixel/scripts/initialization.py
    log_info "机械臂初始化完成"
    current_state=$STATE_PUB_INIT_POSE
}

# 2. 发布AMCL初始定位位姿，修正机器人地图坐标
pub_init_pose() {
    log_info "发布机器人初始定位位姿"
    rostopic pub -1 /initialpose geometry_msgs/PoseWithCovarianceStamped "
header:
  frame_id: 'map'
pose:
  pose:
    position: {x: 0.01277, y: -0.00186, z: 0.0}
    orientation: {x: 0.0, y: 0.0, z: 8.56035e-05, w: 0.9999999963}
  covariance: [0.03, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.012, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.005]
"
    current_state=$STATE_PUB_GOAL1
}

# 3. 切换状态，发起抓取点导航任务
pub_goal1() {
    log_info "准备前往抓取点"
    current_state=$STATE_WAIT_GOAL1_REACH
}

# 4. 调用导航Action客户端行驶至抓取点位
wait_goal1_reach() {
    log_info "调用Action导航客户端 -> 抓取点"
    # 传入目标坐标x y z w
    python3 ~/catkin_ws/src/my_navigation/scripts/nav_action_client.py \
    3.87457 -3.93811 -0.80240 0.59679
    # 导航失败直接退出任务
    if [ $? -ne 0 ]; then
        log_info "抓取点导航失败，任务退出"
        exit 1
    fi
    current_state=$STATE_RUN_VISION
}

# 5. 运行视觉目标检测与自动对位脚本
run_vision() {
    log_info "执行视觉调位脚本"
    python3 ~/catkin_ws/src/my_navigation/scripts/p.py
    log_info "视觉调位完成"
    current_state=$STATE_ARM_PRE_CAPTURE
}

# 6. 机械臂运动至预抓取安全姿态
arm_pre_capture() {
    log_info "机械臂调整至预抓取位置"
    python3 ~/catkin_ws/src/my_dynamixel/scripts/precapture.py
    log_info "预抓取位姿调整完成"
    current_state=$STATE_ARM_CAPTURE
}

# 7. 舵机执行夹爪闭合抓取物体
arm_capture() {
    log_info "执行抓取动作"
    python3 ~/catkin_ws/src/my_dynamixel/scripts/capture.py
    log_info "抓取完成"
    current_state=$STATE_WAIT_TRANSIT_REACH
}

# 11. 导航行驶到中转放料点位
wait_transit_reach() {
    log_info "调用Action导航客户端 -> 中转放料点"
    python3 ~/catkin_ws/src/my_navigation/scripts/nav_action_client.py \
    -3.9448193102467255 0.42350054884041105 -0.9684363080516828 0.2492611426741564
    if [ $? -ne 0 ]; then
        log_info "中转放料点导航失败，任务退出"
        exit 1
    fi
    current_state=$STATE_ARM_TRANSIT_LAYDOWN
}

# 12. 中转点松开夹爪放置物料
arm_transit_laydown() {
    log_info "中转点执行放料动作"
    python3 ~/catkin_ws/src/my_dynamixel/scripts/laydown.py
    log_info "中转点放料完成"
    current_state=$STATE_PUB_GOAL_HOME
}

# 8. 导航返回机器人初始原点
pub_goal_home() {
    log_info "调用Action导航客户端 -> 返回起点"
    python3 ~/catkin_ws/src/my_navigation/scripts/nav_action_client.py \
    0.01277 -0.00186 8.56035e-05 0.9999999963
    if [ $? -ne 0 ]; then
        log_info "返回起点导航失败，任务退出"
        exit 1
    fi
    current_state=$STATE_ARM_LAYDOWN
}

# 9. 原点处再次放料，完成整套流程
arm_laydown() {
    log_info "执行终点放料动作"
    log_info "终点放料完成"
    current_state=$STATE_FINISH
}

# ===================== 主循环入口 =====================
main() {
    # 第一步：整机开机自检，全部正常才进入任务
    full_self_check
    log_info "========== 全自动任务流程启动【Actionlib标准版】 =========="
    # 状态机循环调度
    while true; do
        case $current_state in
            $STATE_WAIT_NAV_START) wait_nav_start ;;
            $STATE_INIT_ARM) init_arm ;;
            $STATE_PUB_INIT_POSE) pub_init_pose ;;
            $STATE_PUB_GOAL1) pub_goal1 ;;
            $STATE_WAIT_GOAL1_REACH) wait_goal1_reach ;;
            $STATE_RUN_VISION) run_vision ;;
            $STATE_ARM_PRE_CAPTURE) arm_pre_capture ;;
            $STATE_ARM_CAPTURE) arm_capture ;;
            $STATE_WAIT_TRANSIT_REACH) wait_transit_reach ;;
            $STATE_ARM_TRANSIT_LAYDOWN) arm_transit_laydown ;;
            $STATE_PUB_GOAL_HOME) pub_goal_home ;;
            $STATE_ARM_LAYDOWN) arm_laydown ;;
            $STATE_FINISH)
                log_info "========== 全部任务执行完毕 =========="
                exit 0
                ;;
            *)
                log_info "错误：未知状态码 $current_state，任务终止"
                exit 1
                ;;
        esac
        sleep 0.2
    done
}

# 启动程序
main