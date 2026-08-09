# OSRacer Base

OSRacer Base 是 OSRacer 的 ROS 2 基础底盘驱动包。它提供速度控制、阿克曼控制、里程计、IMU、RC 原始通道、磁力计和电池状态话题，适合在实车上接入上层导航、遥控或自动驾驶节点。

## 当前维护基线

- `main` 是默认分支，也是唯一持续开发的 ROS 2 主线。2026-08-09 审核的
  profile 对齐代码基线为 `9b4e1a67ab755fa0a22dca7078b4b98c1b8cc3eb`。
  当前包版本为 `0.2.0`，尚未创建 `0.2.0` tag 或 Release。
- `ros1@856323b3912a94860352d87f21f0fcf4a7d7b544` 仅用于兼容；没有明确
  ROS 1 需求时保持不变。
- 上位机契约保持 Proto 1.1，并显式核对 `neo`、`red`、`blue` 的 ProfileID 和
  schema。下游 `osracer/main` 固定依赖不可变 Base commit，不跟随浮动分支。
- 脱敏后的机器可读固件边界位于
  `test/fixtures/proto_1_1/firmware_contract.json`，只包含协议、命令单位、
  ProfileID/schema 和固件硬上限，不包含固件源码、GPIO、PID、NVS、硬件身份
  或车辆标定数据。
- 历史 `v0.1.0` tag 解引用到
  `c7ba366084a56de32cb994048edd1e633090b69e`；它继续作为发布记录保留，
  但不是当前开发基线。

开发记录见 [CHANGELOG.md](CHANGELOG.md)。

现有 Neo 客户交付继续使用完整的 `osracer/product/neo`，本包不替换该冻结交付线。

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
ros2 launch osracer_base chassis_driver.launch.py vehicle_profile:=red
```

必须显式指定 `vehicle_profile`，可选值为 `neo`、`red` 或 `blue`。驱动在启用
stream 前核对固件 `ProjectVer`、`Proto=1.1`、ProfileID、profile schema 和可运动
状态；任何不匹配都会在发送运动命令前关闭连接。

启动成功后，驱动会在日志中打印已核对的固件和 profile 身份，并维护底盘的
ROS 连接状态提示。如果遥控器处于优先控制状态，驱动会提示 ROS 运动指令可能
暂时不会生效。

默认设备路径是 `/dev/osrbot_base`。如果现场设备路径不同，可以手动覆盖：

```bash
ros2 launch osracer_base chassis_driver.launch.py \
  vehicle_profile:=red port:=/dev/ttyACM0
```

查看里程计和 TF：

```bash
ros2 launch osracer_base odom_view.launch.py vehicle_profile:=red
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
| `vehicle_profile` | 必填 | 选择固件和底盘 profile |
| `profile_schema` | 车型文件 | 预期固件 profile schema |
| `wheelbase` | 车型文件 | 车辆轴距，单位 m |
| `max_speed` | 车型文件 | ROS 侧保守速度上限，单位 m/s |
| `speed_mode` | 车型文件 | 速度模式，支持 `high` 和 `low` |
| `max_steering_angle` | 车型文件 | 最大转向角，单位 rad |
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
| `battery_voltage_min` | `10.8` | 仅用于显示映射为 0% 的电压 |
| `battery_voltage_max` | `12.6` | 仅用于显示映射为 100% 的电压 |

### 车型 profile

安装到 `config/vehicles` 的文件只包含 ROS 侧底盘参数：

| Profile | 轴距 | ROS 速度上限 | 转角上限 |
| --- | ---: | ---: | ---: |
| `neo` | 0.285 m | 4.64 m/s | 30 deg |
| `red` | 0.285 m | 4.64 m/s | 30 deg |
| `blue` | 0.325 m | 0.8 m/s | 30 deg |

Neo 和 Red 当前的 ROS 数值相同，但仍保留独立身份。GPIO、编码器 PPR、齿比、
轮径、PID、PWM、NVS 和固件硬安全上限等下位机参数不会复制到这里。

电池电压由固件测量并上传。上述两个电压参数只用于估算
`BatteryState.percentage`，不会影响固件校准、低压保护、告警或运动安全。

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

车辆几何和 ROS 运行限值现在来自选定的车型文件。`/dev/osrbot_base`、frame
名称、watchdog 和电池显示映射等公共参数仍可通过 ROS 参数配置。

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

- 启动时应能在 ROS 日志中看到 `Connected to chassis`，以及通过核对的固件、
  协议和 profile 身份。
- 协议、ProfileID 或 schema 不匹配会按设计拒绝连接；应选择正确的
  `vehicle_profile`，不能覆盖固件身份继续运行。
- 车辆上电后低压告警由底盘独立处理；如果电池电压持续过低，车辆会有声音和灯光提示，并停止执行运动输出。
- 如果 ROS 节点退出或 USB 连接异常，底盘会进入连接丢失提示状态；重新启动节点或重新插拔 USB 后应恢复。
- 如果没有底盘状态提示，先检查 `ros2 run osracer_base check_device`，再确认启动日志里是否打印了固件版本。
