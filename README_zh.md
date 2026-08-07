# OSRacer Base

OSRacer Base 是 OSRacer 的 ROS 2 基础底盘驱动包。它提供速度控制、阿克曼控制、里程计、IMU、RC 原始通道、磁力计和电池状态话题，适合在实车上接入上层导航、遥控或自动驾驶节点。

## 支持环境

- Ubuntu 22.04 + ROS 2 Humble，或 Ubuntu 24.04 + ROS 2 Jazzy
- Python 3
- 可访问 OSRacer 底盘 USB 串口
- ROS 依赖包：
  - `rclpy`
  - `geometry_msgs`
  - `ackermann_msgs`
  - `nav_msgs`
  - `sensor_msgs`
  - `std_msgs`
  - `tf2_ros`
  - `ros2launch`
  - `rviz2`
- 系统依赖：
  - `python3-serial`

Ubuntu 下需要安装 OSRacer udev 规则，并把当前用户加入 `dialout` 组：

```bash
ros2 run osracer_base install_udev_rules
```

安装后重新插拔车辆 USB 线。如果脚本修改了用户组，重新登录系统后生效。

## 安装依赖

Humble:

```bash
sudo apt update
sudo apt install ros-humble-ackermann-msgs ros-humble-rviz2 python3-serial udev
```

Jazzy:

```bash
sudo apt update
sudo apt install ros-jazzy-ackermann-msgs ros-jazzy-rviz2 python3-serial udev
```

## 构建

把本仓库放到 ROS 2 工作空间的 `src` 目录下：

```bash
mkdir -p ~/osracer_ws/src
cd ~/osracer_ws/src
git clone <repo-url> osracer_base
cd ~/osracer_ws
colcon build --symlink-install
source install/setup.bash
```

## 启动

```bash
ros2 launch osracer_base chassis_driver.launch.py
```

启动成功后，驱动会在日志中打印底盘固件 `ProjectVer`，并维护底盘的 ROS 连接状态提示。如果遥控器处于优先控制状态，驱动会提示 ROS 运动指令可能暂时不会生效。

默认设备路径是 `/dev/osrbot_base`。如果现场设备路径不同，可以手动覆盖：

```bash
ros2 launch osracer_base chassis_driver.launch.py port:=/dev/ttyACM0
```

查看里程计和 TF：

```bash
ros2 launch osracer_base odom_view.launch.py
```

发布 SLAM 常用静态 TF 示例：

```bash
ros2 launch osracer_base description.launch.py
```

该示例会补充 `base_footprint`、`base_link`、`imu_link` 和 `laser_frame` 之间的静态坐标关系。激光雷达实际安装位置不同的话，可以用 `laser_x`、`laser_y`、`laser_z`、`laser_yaw` 覆盖。

## ROS 接口

订阅：

```text
/cmd_vel
geometry_msgs/msg/Twist

/ackermann_cmd
ackermann_msgs/msg/AckermannDrive
```

发布：

```text
/odom
nav_msgs/msg/Odometry

/imu/data
sensor_msgs/msg/Imu

/rc_data
std_msgs/msg/Int32MultiArray

/magnetometer_data
sensor_msgs/msg/MagneticField

/battery_state
sensor_msgs/msg/BatteryState
```

两个控制话题可以同时存在，驱动会执行最近收到的控制指令。超过 `cmd_timeout` 没有新指令时，车辆会自动停车。RC、磁力计和电池发布可分别关闭，话题名可配置。

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `port` | `/dev/osrbot_base` | 底盘串口设备 |
| `baudrate` | `460800` | 串口波特率 |
| `wheelbase` | `0.325` | B102 轴距，单位 m |
| `max_speed` | `0.8` | ROS 控制速度上限，单位 m/s |
| `speed_mode` | `high` | 速度模式，支持 `high` 和 `low` |
| `max_steering_angle` | `0.5235987756` | 最大转向角，单位 rad |
| `cmd_timeout` | `0.5` | 控制超时时间，单位 s |
| `reconnect_interval` | `2.0` | 串口重连周期，单位 s |
| `firmware_version_timeout` | `0.3` | 启动时读取底盘固件版本的等待时间，单位 s |
| `connection_status_enabled` | `true` | 是否维护底盘 ROS 连接状态提示 |
| `connection_refresh_period` | `1.0` | 连接状态刷新周期，单位 s |
| `odom_frame_id` | `odom` | 里程计坐标系 |
| `base_frame_id` | `base_footprint` | 车体坐标系 |
| `imu_frame_id` | `imu_link` | IMU 坐标系 |
| `publish_tf` | `true` | 是否发布 `odom` 到车体坐标系的 TF |
| `publish_rc` | `true` | 是否发布 RC 原始通道值 |
| `rc_topic` | `rc_data` | RC 原始通道话题 |
| `publish_mag` | `true` | 是否发布磁力计数据 |
| `mag_topic` | `magnetometer_data` | 磁力计话题 |
| `mag_frame_id` | `imu_link` | 磁力计坐标系 |
| `imu_orientation_covariance` | `[0.02, 0.02, 0.05]` | IMU 姿态 covariance 对角线 |
| `imu_angular_velocity_covariance` | `[0.01, 0.01, 0.01]` | IMU 角速度 covariance 对角线 |
| `imu_linear_acceleration_covariance` | `[0.10, 0.10, 0.10]` | IMU 线加速度 covariance 对角线 |
| `odom_twist_covariance` | `[0.02, 0.20, 1.0, 1.0, 1.0, 0.30]` | 里程计 twist covariance 对角线 |
| `publish_battery` | `true` | 是否发布电池状态 |
| `battery_topic` | `battery_state` | 电池状态话题 |
| `battery_voltage_min` | `10.8` | 映射为 0% 的电压 |
| `battery_voltage_max` | `12.6` | 映射为 100% 的电压 |

### 从已验收 c329 驱动迁移

`osracer_base` 只提供一套 canonical 参数接口。从 `osracer@c329c21` 迁移的上层 launch 必须显式完成以下映射：

| c329 参数 | osracer_base 参数 | 换算 |
| --- | --- | --- |
| `port_name` | `port` | 无 |
| `baud_rate` | `baudrate` | 无 |
| `odom_frame` | `odom_frame_id` | 无 |
| `base_frame` | `base_frame_id` | 无 |
| `imu_frame` | `imu_frame_id` | 无 |
| `max_steering_angle_deg` | `max_steering_angle` | 度换算为弧度 |
| `cmd_watchdog_timeout_s` | `cmd_timeout` | 无 |
| `reconnect_interval_s` | `reconnect_interval` | 无 |
| `firmware_version_timeout_s` | `firmware_version_timeout` | 无 |
| `link_status_enabled` | `connection_status_enabled` | 无 |
| `link_ping_period_s` | `connection_refresh_period` | 无 |
| `mag_frame` | `mag_frame_id` | 无 |

base 自有默认值继续保持 `/dev/osrbot_base`、`wheelbase=0.325`、`max_speed=0.8`、`speed_mode=high` 和 30 度转向上限。

## 控制示例

速度控制：

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.3}, angular: {z: 0.0}}"
```

阿克曼控制：

```bash
ros2 topic pub --once /ackermann_cmd ackermann_msgs/msg/AckermannDrive \
"{speed: 0.3, steering_angle: 0.1}"
```

查看电池状态：

```bash
ros2 topic echo /battery_state
```

检查设备绑定：

```bash
ros2 run osracer_base check_device
```

## 状态提示与排查

- 启动时应能在 ROS 日志中看到 `Connected to chassis` 和 `Chassis firmware ProjectVer`。
- 车辆上电后低压告警由底盘独立处理；如果电池电压持续过低，车辆会有声音和灯光提示，并停止执行运动输出。
- 如果 ROS 节点退出或 USB 连接异常，底盘会进入连接丢失提示状态；重新启动节点或重新插拔 USB 后应恢复。
- 如果没有底盘状态提示，先检查 `ros2 run osracer_base check_device`，再确认启动日志里是否打印了固件版本。
