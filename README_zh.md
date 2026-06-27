# OSRacer Base

OSRacer Base 是 OSRacer 的 ROS 2 基础底盘驱动包。它提供速度控制、阿克曼控制、里程计、IMU 和电池状态话题，适合在实车上接入上层导航、遥控或自动驾驶节点。

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
  - `tf2_ros`
  - `ros2launch`
- 系统依赖：
  - `python3-serial`

Ubuntu 下如果没有串口权限，通常需要把当前用户加入 `dialout` 组：

```bash
sudo usermod -a -G dialout $USER
```

执行后重新登录系统。

## 安装依赖

Humble:

```bash
sudo apt update
sudo apt install ros-humble-ackermann-msgs python3-serial
```

Jazzy:

```bash
sudo apt update
sudo apt install ros-jazzy-ackermann-msgs python3-serial
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
ros2 launch osracer_base chassis_driver.launch.py port:=/dev/ttyACM0
```

如果设备路径不同，替换 `port` 参数即可。

## ROS 接口

订阅：

```text
/cmd_vel
geometry_msgs/msg/Twist

/ackermann_cmd
ackermann_msgs/msg/AckermannDriveStamped
```

发布：

```text
/odom
nav_msgs/msg/Odometry

/imu/data
sensor_msgs/msg/Imu

/battery_state
sensor_msgs/msg/BatteryState
```

两个控制话题可以同时存在，驱动会执行最近收到的控制指令。超过 `cmd_timeout` 没有新指令时，车辆会自动停车。

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `port` | `/dev/ttyACM0` | 底盘串口设备 |
| `baudrate` | `460800` | 串口波特率 |
| `wheelbase` | `0.285` | 轴距，单位 m |
| `max_speed` | `3.0` | 最大速度，单位 m/s |
| `max_steering_angle` | `0.5235987756` | 最大转向角，单位 rad |
| `cmd_timeout` | `0.5` | 控制超时时间，单位 s |
| `odom_frame_id` | `odom` | 里程计坐标系 |
| `base_frame_id` | `base_footprint` | 车体坐标系 |
| `imu_frame_id` | `imu_link` | IMU 坐标系 |
| `publish_tf` | `true` | 是否发布 `odom` 到车体坐标系的 TF |

## 控制示例

速度控制：

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.3}, angular: {z: 0.0}}"
```

阿克曼控制：

```bash
ros2 topic pub --once /ackermann_cmd ackermann_msgs/msg/AckermannDriveStamped \
"{drive: {speed: 0.3, steering_angle: 0.1}}"
```

查看电池状态：

```bash
ros2 topic echo /battery_state
```
