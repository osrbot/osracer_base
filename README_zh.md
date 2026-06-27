# OSRacer Base

当前分支适用于 ROS 1 Noetic；ROS 2 用户请切换到 `ros2` 分支。

OSRacer Base 是 OSRacer 的 ROS 1 基础底盘驱动包。它提供速度控制、阿克曼控制、里程计、IMU 和电池状态话题，适合在实车上接入上层导航、遥控或自动驾驶节点。

## 支持环境

- Ubuntu 20.04 + ROS 1 Noetic
- Python 3
- 可访问 OSRacer 底盘 USB 串口
- ROS 依赖包：
  - `rospy`
  - `geometry_msgs`
  - `ackermann_msgs`
  - `nav_msgs`
  - `rospkg`
  - `sensor_msgs`
  - `tf2_ros`
  - `roslaunch`
  - `rviz`
- 系统依赖：
  - `python3-serial`

Ubuntu 下需要安装 OSRacer udev 规则，并把当前用户加入 `dialout` 组：

```bash
rosrun osracer_base install_udev_rules.py
```

安装后重新插拔车辆 USB 线。如果脚本修改了用户组，重新登录系统后生效。

## 安装依赖

```bash
sudo apt update
sudo apt install ros-noetic-ackermann-msgs ros-noetic-rviz python3-rospkg python3-serial udev
```

## 构建

把本仓库放到 catkin 工作空间的 `src` 目录下：

```bash
mkdir -p ~/osracer_ws/src
cd ~/osracer_ws/src
git clone -b ros1 <repo-url> osracer_base
cd ~/osracer_ws
catkin_make
source devel/setup.bash
```

## 启动

```bash
roslaunch osracer_base chassis_driver.launch
```

启动成功后，驱动会在日志中打印底盘固件 `ProjectVer`，并维护底盘的 ROS 连接状态提示。如果遥控器处于优先控制状态，驱动会提示 ROS 运动指令可能暂时不会生效。

默认设备路径是 `/dev/osrbot_base`。如果现场设备路径不同，可以手动覆盖：

```bash
roslaunch osracer_base chassis_driver.launch port:=/dev/ttyACM0
```

查看里程计和 TF：

```bash
roslaunch osracer_base odom_view.launch
```

发布 SLAM 常用静态 TF 示例：

```bash
roslaunch osracer_base description.launch
```

该示例会补充 `base_footprint`、`base_link`、`imu_link` 和 `laser_frame` 之间的静态坐标关系。激光雷达实际安装位置不同的话，可以用 `laser_x`、`laser_y`、`laser_z`、`laser_yaw` 覆盖。

## ROS 接口

订阅：

```text
/cmd_vel
geometry_msgs/Twist

/ackermann_cmd
ackermann_msgs/AckermannDriveStamped
```

发布：

```text
/odom
nav_msgs/Odometry

/imu/data
sensor_msgs/Imu

/battery_state
sensor_msgs/BatteryState
```

两个控制话题可以同时存在，驱动会执行最近收到的控制指令。超过 `cmd_timeout` 没有新指令时，车辆会自动停车。

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `port` | `/dev/osrbot_base` | 底盘串口设备 |
| `baudrate` | `460800` | 串口波特率 |
| `wheelbase` | `0.325` | B102 轴距，单位 m |
| `max_speed` | `1.5` | ROS 控制速度上限，单位 m/s；参数填大也会限制到 `1.5` |
| `speed_mode` | `high` | `high` 使用 `max_speed`，`low` 使用 `max_speed * 0.15` |
| `max_steering_angle` | `0.5235987756` | 最大转向角，单位 rad |
| `cmd_timeout` | `0.5` | 控制超时时间，单位 s |
| `firmware_version_timeout` | `0.5` | 启动时读取底盘固件版本的等待时间，单位 s |
| `connection_status_enabled` | `true` | 是否维护底盘 ROS 连接状态提示 |
| `connection_refresh_period` | `1.0` | 连接状态刷新周期，单位 s |
| `odom_frame_id` | `odom` | 里程计坐标系 |
| `base_frame_id` | `base_footprint` | 车体坐标系 |
| `imu_frame_id` | `imu_link` | IMU 坐标系 |
| `publish_tf` | `true` | 是否发布 `odom` 到车体坐标系的 TF |

## 控制示例

速度控制：

```bash
rostopic pub -1 /cmd_vel geometry_msgs/Twist \
"{linear: {x: 0.3}, angular: {z: 0.0}}"
```

阿克曼控制：

```bash
rostopic pub -1 /ackermann_cmd ackermann_msgs/AckermannDriveStamped \
"{drive: {speed: 0.3, steering_angle: 0.1}}"
```

查看电池状态：

```bash
rostopic echo /battery_state
```

检查设备绑定：

```bash
rosrun osracer_base check_device.py
```

## 状态提示与排查

- 启动时应能在 ROS 日志中看到 `Connected to chassis` 和 `Chassis firmware ProjectVer`。
- 车辆上电后低压告警由底盘独立处理；如果电池电压持续过低，车辆会有声音和灯光提示，并停止执行运动输出。
- 如果 ROS 节点退出或 USB 连接异常，底盘会进入连接丢失提示状态；重新启动节点或重新插拔 USB 后应恢复。
- 如果没有底盘状态提示，先检查 `rosrun osracer_base check_device.py`，再确认启动日志里是否打印了固件版本。
