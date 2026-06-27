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
  - `rviz2`
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
sudo apt install ros-humble-ackermann-msgs ros-humble-rviz2 python3-serial udev
```

Jazzy:

```bash
sudo apt update
sudo apt install ros-jazzy-ackermann-msgs ros-jazzy-rviz2 python3-serial udev
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

After startup, the driver logs the chassis firmware `ProjectVer` and maintains the chassis ROS connection status indicator. If the RC transmitter is in priority control mode, the driver warns that ROS motion commands may be ignored until serial control is selected.

The default device path is `/dev/osrbot_base`. Use a different `port` value only when needed:

```bash
ros2 launch osracer_base chassis_driver.launch.py port:=/dev/ttyACM0
```

View odometry and TF in RViz:

```bash
ros2 launch osracer_base odom_view.launch.py
```

Publish a static TF example for SLAM bringup:

```bash
ros2 launch osracer_base description.launch.py
```

The example provides static transforms between `base_footprint`, `base_link`, `imu_link`, and `laser_frame`. Override `laser_x`, `laser_y`, `laser_z`, and `laser_yaw` if the LiDAR mounting position is different.

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
| `wheelbase` | `0.325` | B102 wheelbase in meters |
| `max_speed` | `1.5` | ROS control speed limit in m/s; larger values are capped at `1.5` |
| `speed_mode` | `high` | `high` uses `max_speed`; `low` uses `max_speed * 0.15` |
| `max_steering_angle` | `0.5235987756` | Maximum steering angle in radians |
| `cmd_timeout` | `0.5` | Command timeout in seconds |
| `firmware_version_timeout` | `0.5` | Startup wait time for reading chassis firmware version, in seconds |
| `connection_status_enabled` | `true` | Maintain chassis ROS connection status indicator |
| `connection_refresh_period` | `1.0` | Connection status refresh period in seconds |
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

## Status Indicators and Troubleshooting

- On startup, the ROS log should show `Connected to chassis` and `Chassis firmware ProjectVer`.
- Low-voltage alerts are handled by the chassis itself. If battery voltage stays too low, the vehicle uses sound and light indicators and stops motion output.
- If the ROS node exits or USB connection is lost, the chassis enters its connection-lost indicator state. Restarting the node or reconnecting USB should recover it.
- If chassis status indicators do not appear, run `ros2 run osracer_base check_device` first, then confirm the startup log prints the firmware version.
