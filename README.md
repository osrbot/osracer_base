# OSRacer Base

OSRacer Base is the minimal ROS 2 chassis driver package for OSRacer. It exposes velocity control, Ackermann control, odometry, IMU, and battery status topics for real vehicle bringup.

## Requirements

- Ubuntu 22.04 + ROS 2 Humble, or Ubuntu 24.04 + ROS 2 Jazzy
- Python 3
- Access to the OSRacer USB serial device
- ROS packages:
  - `rclpy`
  - `geometry_msgs`
  - `ackermann_msgs`
  - `nav_msgs`
  - `sensor_msgs`
  - `tf2_ros`
  - `ros2launch`
- System package:
  - `python3-serial`

On Ubuntu, install the OSRacer udev rule and add your user to the `dialout` group:

```bash
ros2 run osracer_base install_udev_rules
```

Unplug and reconnect the vehicle USB cable after installing the rule. Log out and log back in if your group membership changed.

## Install Dependencies

Humble:

```bash
sudo apt update
sudo apt install ros-humble-ackermann-msgs python3-serial udev
```

Jazzy:

```bash
sudo apt update
sudo apt install ros-jazzy-ackermann-msgs python3-serial udev
```

## Build

Place this repository in a ROS 2 workspace:

```bash
mkdir -p ~/osracer_ws/src
cd ~/osracer_ws/src
git clone <repo-url> osracer_base
cd ~/osracer_ws
colcon build --symlink-install
source install/setup.bash
```

## Launch

```bash
ros2 launch osracer_base chassis_driver.launch.py
```

The default device path is `/dev/osrbot_base`. Use a different `port` value only when needed:

```bash
ros2 launch osracer_base chassis_driver.launch.py port:=/dev/ttyACM0
```

## ROS API

Subscriptions:

```text
/cmd_vel
geometry_msgs/msg/Twist

/ackermann_cmd
ackermann_msgs/msg/AckermannDriveStamped
```

Publications:

```text
/odom
nav_msgs/msg/Odometry

/imu/data
sensor_msgs/msg/Imu

/battery_state
sensor_msgs/msg/BatteryState
```

Both control topics can be used. The driver applies the most recent command. If no command is received within `cmd_timeout`, the vehicle stops.

## Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `port` | `/dev/osrbot_base` | Chassis serial device |
| `baudrate` | `460800` | Serial baud rate |
| `wheelbase` | `0.285` | Wheelbase in meters |
| `max_speed` | `3.0` | Maximum speed in m/s |
| `max_steering_angle` | `0.5235987756` | Maximum steering angle in radians |
| `cmd_timeout` | `0.5` | Command timeout in seconds |
| `odom_frame_id` | `odom` | Odometry frame |
| `base_frame_id` | `base_footprint` | Vehicle base frame |
| `imu_frame_id` | `imu_link` | IMU frame |
| `publish_tf` | `true` | Publish odometry TF |

## Examples

Velocity command:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.3}, angular: {z: 0.0}}"
```

Ackermann command:

```bash
ros2 topic pub --once /ackermann_cmd ackermann_msgs/msg/AckermannDriveStamped \
"{drive: {speed: 0.3, steering_angle: 0.1}}"
```

Battery status:

```bash
ros2 topic echo /battery_state
```

Device check:

```bash
ros2 run osracer_base check_device
```
