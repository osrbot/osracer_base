# OSRacer Base

<!-- markdownlint-disable MD013 MD033 -->

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./README_zh.md">简体中文</a>
</p>

<p align="center">
  <img src="docs/assets/readme/osracer-base-hero.jpg" alt="OSRacer Base ROS 2 底盘接口" width="100%">
</p>

<p align="center">
  <strong>面向智能车辆应用的 ROS 2 运动控制与状态感知接口。</strong>
</p>

<p align="center">
  <a href="https://github.com/osrbot/osracer_base/actions/workflows/ros2-ci.yml"><img src="https://github.com/osrbot/osracer_base/actions/workflows/ros2-ci.yml/badge.svg" alt="ROS 2 CI"></a>
  <a href="https://docs.ros.org/en/humble/"><img src="https://img.shields.io/badge/ROS%202-Humble-22314E?logo=ros" alt="ROS 2 Humble"></a>
  <a href="https://docs.ros.org/en/jazzy/"><img src="https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros" alt="ROS 2 Jazzy"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-2EA44F" alt="MIT License"></a>
</p>

通过标准 ROS 2 接口连接车辆控制与状态感知，为路径跟踪、定位导航及自主驾驶应用提供底盘接入。

## 核心能力

### 统一运动控制

支持速度与 Ackermann 转向指令，上层应用无需直接处理串口通信。

### 同步状态感知

同步发布运动与惯性数据，采用统一时间戳，为定位和状态估计提供输入。

### 连续连接与运行保护

支持连接检查、自动重连、异常数据过滤和指令超时停车请求。

### 标准 ROS 2 集成

提供标准话题、可配置坐标系和 RViz 可视化入口。

## 运行环境

| 操作系统 | ROS 2 发行版 |
| --- | --- |
| Ubuntu 22.04 | Humble |
| Ubuntu 24.04 | Jazzy |

请先安装对应 ROS 2 环境。以下命令使用 Bash；Python、ROS 消息及串口等依赖由 `rosdep` 安装。

## 快速开始

安装构建工具并加载 ROS 环境。Jazzy 用户将下面的 `humble` 替换为 `jazzy`：

```bash
source /opt/ros/humble/setup.bash
sudo apt update
sudo apt install git python3-rosdep python3-colcon-common-extensions python3-pytest
```

仅首次使用 rosdep 时执行 `sudo rosdep init`。

```bash
rosdep update
mkdir -p ~/osracer_base_ws/src
cd ~/osracer_base_ws/src
git clone https://github.com/osrbot/osracer_base.git
```

请使用车辆配套的驱动版本；如需升级，请先联系 [技术支持](mailto:winter@osrbot.com) 确认兼容性。

```bash
cd ~/osracer_base_ws
rosdep install --from-paths src --ignore-src --rosdistro "$ROS_DISTRO" -r -y
colcon build --packages-select osracer_base --symlink-install
source install/setup.bash
ros2 pkg prefix osracer_base
```

确认包路径位于本工作空间的 `install` 目录。新终端中加载环境，自定义工作空间请替换路径：

```bash
source /opt/ros/humble/setup.bash
source ~/osracer_base_ws/install/setup.bash
```

## 设备配置

每台 Linux 系统只需安装一次 udev 规则：

```bash
ros2 run osracer_base install_udev_rules
```

安装后重新连接 USB。如果当前用户刚加入 `dialout` 用户组，请注销后重新登录。

无需启动 ROS 节点即可检查设备：

```bash
ros2 run osracer_base check_device
```

## 启动

连接车辆 USB，并关闭其他占用底盘串口的程序，然后启动一份驱动：

```bash
ros2 launch osracer_base chassis_driver.launch.py
```

默认串口设备为 `/dev/osrbot_base`。仅在确有需要时修改：

```bash
ros2 launch osracer_base chassis_driver.launch.py \
  port:=/dev/ttyACM0
```

如需同时启动 RViz，改用以下入口：

```bash
ros2 launch osracer_base odom_view.launch.py
```

两种启动方式二选一，避免重复运行驱动。静态 TF 示例见 `description.launch.py`，使用前按实际安装位置配置。

## 连接与数据检查

连接成功时日志会出现 `Connected to chassis`。在已加载相同环境的另一终端检查：

```bash
ros2 node list
ros2 topic list -t
ros2 topic echo /battery_state --once
ros2 topic echo /odom --once
ros2 topic echo /imu/data --once
ros2 topic hz /odom
```

确认数据持续更新且数值合理，按 Ctrl+C 结束频率观察。异常情况见“故障处理”。

## ROS 接口

### 订阅

| 话题 | 类型 | 用途 |
| --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 线速度与角速度命令 |
| `/ackermann_cmd` | `ackermann_msgs/msg/AckermannDrive` | 速度与转角命令 |

驱动采用最近收到的有效命令；输入须为有限数值，无效输入会触发停车请求。
通信中断后自动重连，通过连接校验后才处理新的运动指令。

### 发布

| 话题 | 类型 | 用途 |
| --- | --- | --- |
| `/odom` | `nav_msgs/msg/Odometry` | 底盘里程计 |
| `/imu/data` | `sensor_msgs/msg/Imu` | 姿态、角速度与加速度 |
| `/rc_data` | `std_msgs/msg/Int32MultiArray` | 遥控器原始通道 |
| `/magnetometer_data` | `sensor_msgs/msg/MagneticField` | 磁场测量值 |
| `/battery_state` | `sensor_msgs/msg/BatteryState` | 电池电压与显示电量 |

遥控器、磁力计、电池状态和里程计 TF 可以分别启用或关闭。

## 配置

常用启动参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `port` | `/dev/osrbot_base` | 底盘串口设备 |
| `baudrate` | `460800` | 串口波特率 |
| `cmd_timeout` | `0.5` | 未收到有效命令后请求停车的超时时间，单位为秒 |
| `reconnect_interval` | `2.0` | 串口重连间隔，单位为秒 |
| `odom_frame_id` | `odom` | 里程计坐标系 |
| `base_frame_id` | `base_footprint` | 车辆基础坐标系 |
| `imu_frame_id` | `imu_link` | IMU 坐标系 |
| `publish_tf` | `true` | 发布里程计 TF |
| `publish_rc` | `true` | 发布遥控器通道 |
| `publish_mag` | `true` | 发布磁场数据 |
| `publish_battery` | `true` | 发布电池状态 |

`/battery_state` 提供电池电压和基于电压估算的电量百分比，供运行监测参考。

## 控制示例

首次运行前，稳固支撑车辆使驱动轮悬空、转向无遮挡，并准备停机手段。
按车辆说明切换到主机控制模式，只运行一个运动命令发布程序。以下示例会产生运动，数值不代表产品限速。

发送一次速度命令（线速度单位为 m/s，角速度单位为 rad/s）：

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3}, angular: {z: 0.0}}"
```

停稳后，可单独发送一次 Ackermann 命令（速度单位为 m/s，转角单位为 rad）：

```bash
ros2 topic pub --once /ackermann_cmd ackermann_msgs/msg/AckermannDrive \
  "{speed: 0.3, steering_angle: 0.1}"
```

`--once` 仅发送一次；持续控制时，发送间隔应小于 `cmd_timeout`。
超时后驱动请求零速和转向回中，实际停稳时间取决于车辆状态。

主动结束运动时，先停止其他运动发布程序，再发送零速：

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

确认车辆停稳后再退出驱动。ROS 停车命令依赖通信和当前控制源，不能代替现场停机手段。

## 故障处理

| 现象 | 建议处理方式 |
| --- | --- |
| 找不到 `/dev/osrbot_base` | 重新安装 udev 规则、连接 USB，并确认当前用户属于 `dialout` 用户组。 |
| 打开串口时权限不足 | 确认用户组设置，然后注销并重新登录。 |
| 串口被占用 | 停止正在使用底盘设备的其他 ROS 节点或工具。 |
| 驱动报告接口不匹配 | 保留错误信息并联系技术支持。 |
| 命令无法驱动车辆 | 检查连接日志、遥控器优先级、命令话题与超时设置。 |
| 话题没有数据 | 运行 `check_device`，重启驱动并检查话题频率。 |

如需技术协助，请通过 [GitHub Issues](https://github.com/osrbot/osracer_base/issues)
或 [winter@osrbot.com](mailto:winter@osrbot.com) 联系我们。

## 作者

- Zhihao ZHANG
- Kit So
- Jintai WANG
- dajianli
