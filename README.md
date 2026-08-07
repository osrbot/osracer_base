# OSRacer Base

OSRacer Base is the minimal ROS 2 chassis driver package for OSRacer. It exposes velocity control, Ackermann control, odometry, IMU, raw RC, magnetometer, and battery status topics for real vehicle bringup.

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
  - `std_msgs`
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
ackermann_msgs/msg/AckermannDrive
```

Publications:

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

Both control topics can be used. The driver applies the most recent command. If no command is received within `cmd_timeout`, the vehicle stops. RC, magnetometer, and battery publication can be disabled independently, and their topic names are configurable.

## Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `port` | `/dev/osrbot_base` | Chassis serial device |
| `baudrate` | `460800` | Serial baud rate |
| `wheelbase` | `0.325` | B102 wheelbase in meters |
| `max_speed` | `0.8` | ROS control speed limit in m/s |
| `speed_mode` | `high` | Speed mode, supports `high` and `low` |
| `max_steering_angle` | `0.5235987756` | Maximum steering angle in radians |
| `cmd_timeout` | `0.5` | Command timeout in seconds |
| `reconnect_interval` | `2.0` | Serial reconnect interval in seconds |
| `firmware_version_timeout` | `0.3` | Startup wait time for reading chassis firmware version, in seconds |
| `connection_status_enabled` | `true` | Maintain chassis ROS connection status indicator |
| `connection_refresh_period` | `1.0` | Connection status refresh period in seconds |
| `odom_frame_id` | `odom` | Odometry frame |
| `base_frame_id` | `base_footprint` | Vehicle base frame |
| `imu_frame_id` | `imu_link` | IMU frame |
| `publish_tf` | `true` | Publish odometry TF |
| `publish_rc` | `true` | Publish raw RC channel values |
| `rc_topic` | `rc_data` | Raw RC topic |
| `publish_mag` | `true` | Publish magnetometer data |
| `mag_topic` | `magnetometer_data` | Magnetometer topic |
| `mag_frame_id` | `imu_link` | Magnetometer frame |
| `imu_orientation_covariance` | `[0.02, 0.02, 0.05]` | IMU orientation covariance diagonal |
| `imu_angular_velocity_covariance` | `[0.01, 0.01, 0.01]` | IMU angular velocity covariance diagonal |
| `imu_linear_acceleration_covariance` | `[0.10, 0.10, 0.10]` | IMU linear acceleration covariance diagonal |
| `odom_twist_covariance` | `[0.02, 0.20, 1.0, 1.0, 1.0, 0.30]` | Odometry twist covariance diagonal |
| `publish_battery` | `true` | Publish battery state |
| `battery_topic` | `battery_state` | Battery topic |
| `battery_voltage_min` | `10.8` | Voltage mapped to 0% |
| `battery_voltage_max` | `12.6` | Voltage mapped to 100% |

### Migration from the accepted c329 driver

`osracer_base` intentionally exposes one canonical parameter API. A downstream launch file migrating from `osracer@c329c21` must map the old names explicitly:

| c329 parameter | osracer_base parameter | Conversion |
| --- | --- | --- |
| `port_name` | `port` | None |
| `baud_rate` | `baudrate` | None |
| `odom_frame` | `odom_frame_id` | None |
| `base_frame` | `base_frame_id` | None |
| `imu_frame` | `imu_frame_id` | None |
| `max_steering_angle_deg` | `max_steering_angle` | Degrees to radians |
| `cmd_watchdog_timeout_s` | `cmd_timeout` | None |
| `reconnect_interval_s` | `reconnect_interval` | None |
| `firmware_version_timeout_s` | `firmware_version_timeout` | None |
| `link_status_enabled` | `connection_status_enabled` | None |
| `link_ping_period_s` | `connection_refresh_period` | None |
| `mag_frame` | `mag_frame_id` | None |

The base-specific defaults remain `/dev/osrbot_base`, `wheelbase=0.325`, `max_speed=0.8`, `speed_mode=high`, and a 30-degree steering limit.

## Examples

Velocity command:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.3}, angular: {z: 0.0}}"
```

Ackermann command:

```bash
ros2 topic pub --once /ackermann_cmd ackermann_msgs/msg/AckermannDrive \
"{speed: 0.3, steering_angle: 0.1}"
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
