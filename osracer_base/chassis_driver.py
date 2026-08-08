import math
import os
import re
import signal
import termios
import threading
import time

import rclpy
from ackermann_msgs.msg import AckermannDrive
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile
from sensor_msgs.msg import BatteryState, Imu, MagneticField
from std_msgs.msg import Int32MultiArray
from tf2_ros import TransformBroadcaster

import serial


DEFAULT_MAX_SPEED = 0.8
LOW_SPEED_RATIO = 0.5
SUPPORTED_PROTOCOL = '1.1'
SERIAL_ERRORS = (serial.SerialException, OSError, ValueError, TypeError, termios.error)


class ChassisDriver(Node):
    def __init__(self):
        super().__init__('osracer_base')

        self.declare_parameter('port', '/dev/osrbot_base')
        self.declare_parameter('baudrate', 460800)
        self.declare_parameter('vehicle_profile', '')
        self.declare_parameter('profile_schema', 1)
        self.declare_parameter('wheelbase', 0.325)
        self.declare_parameter('max_speed', DEFAULT_MAX_SPEED)
        self.declare_parameter('speed_mode', 'high')
        self.declare_parameter('max_steering_angle', math.radians(30.0))
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('reconnect_interval', 2.0)
        self.declare_parameter('firmware_version_timeout', 0.3)
        self.declare_parameter('connection_status_enabled', True)
        self.declare_parameter('connection_refresh_period', 1.0)
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_footprint')
        self.declare_parameter('imu_frame_id', 'imu_link')
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('publish_rc', True)
        self.declare_parameter('rc_topic', 'rc_data')
        self.declare_parameter('publish_mag', True)
        self.declare_parameter('mag_topic', 'magnetometer_data')
        self.declare_parameter('mag_frame_id', 'imu_link')
        self.declare_parameter('imu_orientation_covariance', [0.02, 0.02, 0.05])
        self.declare_parameter('imu_angular_velocity_covariance', [0.01, 0.01, 0.01])
        self.declare_parameter('imu_linear_acceleration_covariance', [0.10, 0.10, 0.10])
        self.declare_parameter('odom_twist_covariance', [0.02, 0.20, 1.0, 1.0, 1.0, 0.30])
        self.declare_parameter('publish_battery', True)
        self.declare_parameter('battery_topic', 'battery_state')
        self.declare_parameter('battery_voltage_min', 10.8)
        self.declare_parameter('battery_voltage_max', 12.6)

        self.port = self.get_parameter('port').value
        self.baudrate = int(self.get_parameter('baudrate').value)
        self.vehicle_profile = str(self.get_parameter('vehicle_profile').value).strip().lower()
        self.profile_schema = int(self.get_parameter('profile_schema').value)
        if not re.fullmatch(r'[a-z0-9_-]+', self.vehicle_profile):
            raise ValueError('vehicle_profile must be selected explicitly')
        if self.profile_schema < 1:
            raise ValueError('profile_schema must be positive')
        self.wheelbase = float(self.get_parameter('wheelbase').value)
        self.max_speed = self.resolve_max_speed(
            self.get_parameter('max_speed').value,
            self.get_parameter('speed_mode').value,
        )
        self.max_steering_angle = abs(float(self.get_parameter('max_steering_angle').value))
        self.cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self.reconnect_interval = float(self.get_parameter('reconnect_interval').value)
        self.firmware_version_timeout = float(self.get_parameter('firmware_version_timeout').value)
        self.connection_status_enabled = self.as_bool(self.get_parameter('connection_status_enabled').value)
        self.connection_refresh_period = float(self.get_parameter('connection_refresh_period').value)
        self.odom_frame_id = self.get_parameter('odom_frame_id').value
        self.base_frame_id = self.get_parameter('base_frame_id').value
        self.imu_frame_id = self.get_parameter('imu_frame_id').value
        self.publish_tf = self.as_bool(self.get_parameter('publish_tf').value)
        self.publish_rc_enabled = self.as_bool(self.get_parameter('publish_rc').value)
        self.rc_topic = self.get_parameter('rc_topic').value
        self.publish_mag_enabled = self.as_bool(self.get_parameter('publish_mag').value)
        self.mag_topic = self.get_parameter('mag_topic').value
        self.mag_frame_id = self.get_parameter('mag_frame_id').value
        self.imu_orientation_covariance = self.diagonal_covariance(
            self.get_parameter('imu_orientation_covariance').value
        )
        self.imu_angular_velocity_covariance = self.diagonal_covariance(
            self.get_parameter('imu_angular_velocity_covariance').value
        )
        self.imu_linear_acceleration_covariance = self.diagonal_covariance(
            self.get_parameter('imu_linear_acceleration_covariance').value
        )
        self.odom_twist_covariance = self.diagonal_covariance_6d(
            self.get_parameter('odom_twist_covariance').value
        )
        self.publish_battery_enabled = self.as_bool(self.get_parameter('publish_battery').value)
        self.battery_topic = self.get_parameter('battery_topic').value
        self.battery_voltage_min = float(self.get_parameter('battery_voltage_min').value)
        self.battery_voltage_max = float(self.get_parameter('battery_voltage_max').value)

        qos_fast = QoSProfile(depth=1)
        qos_normal = QoSProfile(depth=5)
        self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, qos_normal)
        self.create_subscription(
            AckermannDrive,
            'ackermann_cmd',
            self.ackermann_cmd_callback,
            qos_normal,
        )
        self.odom_pub = self.create_publisher(Odometry, 'odom', qos_fast)
        self.imu_pub = self.create_publisher(Imu, 'imu/data', qos_fast)
        self.rc_pub = (
            self.create_publisher(Int32MultiArray, self.rc_topic, qos_normal)
            if self.publish_rc_enabled else None
        )
        self.mag_pub = (
            self.create_publisher(MagneticField, self.mag_topic, qos_fast)
            if self.publish_mag_enabled else None
        )
        self.battery_pub = (
            self.create_publisher(BatteryState, self.battery_topic, qos_normal)
            if self.publish_battery_enabled else None
        )
        self.tf_broadcaster = TransformBroadcaster(self) if self.publish_tf else None

        self.serial_conn = None
        self.serial_lock = threading.Lock()
        self.reader_thread = None
        self.shutdown_event = threading.Event()
        self.last_cmd_time = self.get_clock().now()
        self.remote_control_active = None

        self.create_timer(self.reconnect_interval, self.ensure_connected)
        self.create_timer(0.1, self.watchdog_check)
        self.create_timer(max(0.2, self.connection_refresh_period), self.refresh_connection_status)
        self.get_logger().info(f"ROS speed limit: {self.max_speed:.3f} m/s")
        self.ensure_connected()

    def ensure_connected(self):
        if self.shutdown_event.is_set():
            return
        with self.serial_lock:
            conn = self.serial_conn
            connected = conn is not None and conn.is_open
        if connected:
            if self.port.startswith('/') and not os.path.exists(self.port):
                self.get_logger().warning(f"Serial device disconnected: {self.port}")
                self.close_serial(conn)
                return
            self.start_reader()
            return

        if self.port.startswith('/') and not os.path.exists(self.port):
            self.get_logger().warning(f"Serial device not found: {self.port}")
            return

        try:
            conn = serial.Serial(self.port, self.baudrate, timeout=0.1, write_timeout=0.1)
            conn.reset_input_buffer()
            conn.reset_output_buffer()
        except SERIAL_ERRORS as exc:
            self.get_logger().warning(f"Could not open serial device {self.port}: {exc}")
            return

        with self.serial_lock:
            self.serial_conn = conn
        if not self.configure_device():
            self.close_serial()
            return
        self.start_reader()
        self.get_logger().info(f"Connected to chassis on {self.port}")

    def configure_device(self):
        if not self.verify_firmware_identity():
            return False
        if not self.write_raw(self._device_mode_command()):
            return False
        if not self.write_raw(self._state_request_command()):
            return False
        self.send_connection_status('up')
        return True

    @staticmethod
    def _device_mode_command():
        return ''.join(chr(value) for value in (115, 116, 114, 101, 97, 109, 32, 115, 121, 110, 99, 10))

    @staticmethod
    def _state_request_command():
        return chr(115) + '\n'

    @staticmethod
    def _quiet_command():
        return ''.join(chr(value) for value in (115, 116, 114, 101, 97, 109, 32, 111, 102, 102, 10))

    @staticmethod
    def _version_command():
        return ''.join(chr(value) for value in (102, 119, 32, 118, 101, 114, 115, 105, 111, 110, 10))

    @staticmethod
    def _profile_command():
        return 'profile get\n'

    def verify_firmware_identity(self):
        with self.serial_lock:
            conn = self.serial_conn
            if conn is None or not conn.is_open:
                return False
            try:
                conn.reset_input_buffer()
                conn.write(self._quiet_command().encode('utf-8'))
                conn.flush()
                time.sleep(0.05)
                conn.reset_input_buffer()
                conn.write(self._version_command().encode('utf-8'))
                conn.flush()
            except SERIAL_ERRORS as exc:
                self.get_logger().warning(f"Could not query chassis firmware version: {exc}")
                return False

        version = self.read_identity_response(self.parse_firmware_version)
        if version is None:
            self.get_logger().warning('Chassis firmware identity unavailable')
            return False
        project_ver, protocol = version
        if protocol != SUPPORTED_PROTOCOL:
            self.get_logger().warning(
                f"Unsupported chassis protocol {protocol}; expected {SUPPORTED_PROTOCOL}"
            )
            return False

        if not self.write_raw(self._profile_command()):
            return False
        profile = self.read_identity_response(self.parse_profile_status)
        if profile is None:
            self.get_logger().warning('Chassis profile identity unavailable')
            return False
        if profile['id'] != self.vehicle_profile or profile['schema'] != self.profile_schema:
            self.get_logger().warning(
                'Chassis profile mismatch: '
                f"device={profile['id']}/schema-{profile['schema']} "
                f"selected={self.vehicle_profile}/schema-{self.profile_schema}"
            )
            return False
        if profile['state'] != 'READY' or not profile['motion']:
            self.get_logger().warning(
                'Chassis profile is not motion-ready: '
                f"State={profile['state']}, Motion={'Yes' if profile['motion'] else 'No'}"
            )
            return False

        self.get_logger().info(
            f"Chassis firmware ProjectVer: {project_ver}, Proto: {protocol}, "
            f"Profile: {profile['id']}/schema-{profile['schema']}, State: {profile['state']}"
        )
        return True

    def read_identity_response(self, parser):
        deadline = time.monotonic() + max(0.1, self.firmware_version_timeout)
        while time.monotonic() < deadline:
            with self.serial_lock:
                conn = self.serial_conn
                if conn is None or not conn.is_open:
                    return None
                try:
                    line = conn.readline().decode('utf-8', errors='ignore').strip()
                except SERIAL_ERRORS as exc:
                    self.get_logger().warning(f"Could not read chassis identity: {exc}")
                    return None
            if line:
                result = parser(line)
                if result is not None:
                    return result
        return None

    @staticmethod
    def parse_firmware_version(line):
        project_match = re.search(r'\bProjectVer\s*[:=]\s*([^,\s]+)', line)
        protocol_match = re.search(r'\bProto\s*[:=]\s*([0-9]+(?:\.[0-9]+)*)', line)
        if project_match and protocol_match:
            return project_match.group(1), protocol_match.group(1)
        return None

    @staticmethod
    def parse_project_version(line):
        identity = ChassisDriver.parse_firmware_version(line)
        if identity:
            return identity[0]
        match = re.search(r'\bProjectVer\s*[:=]\s*([^,\s]+)', line)
        if match:
            return match.group(1)
        match = re.search(r'\bProjectVer\s+([^,\s]+)', line)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def parse_profile_status(line):
        match = re.fullmatch(
            r'PROFILE:\s+ID=([a-z0-9_-]+),\s+Schema=([0-9]+),\s+'
            r'State=([A-Z0-9_]+),\s+Motion=(Yes|No),\s+Writes=(Yes|No)',
            line,
        )
        if not match:
            return None
        return {
            'id': match.group(1),
            'schema': int(match.group(2)),
            'state': match.group(3),
            'motion': match.group(4) == 'Yes',
            'writes': match.group(5) == 'Yes',
        }

    def start_reader(self):
        if self.shutdown_event.is_set():
            return
        if self.reader_thread and self.reader_thread.is_alive():
            return
        self.reader_thread = threading.Thread(target=self.read_loop, daemon=True)
        self.reader_thread.start()

    def close_serial(self, expected_conn=None):
        with self.serial_lock:
            if expected_conn is not None and self.serial_conn is not expected_conn:
                conn = expected_conn
            else:
                conn = self.serial_conn
                self.serial_conn = None
        if conn:
            try:
                if conn.is_open:
                    self.write_connection_down(conn)
                conn.close()
            except Exception:
                pass

    def send_connection_status(self, state):
        if not self.connection_status_enabled:
            return True
        return self.write_raw(self._connection_status_command(state))

    def refresh_connection_status(self):
        if self.shutdown_event.is_set():
            return
        with self.serial_lock:
            connected = self.serial_conn is not None and self.serial_conn.is_open
        if connected:
            self.send_connection_status('ping')

    def write_connection_down(self, conn):
        if not self.connection_status_enabled:
            return
        try:
            conn.write(self._connection_status_command('down').encode('utf-8'))
            conn.flush()
        except SERIAL_ERRORS:
            pass

    @staticmethod
    def _connection_status_command(state):
        values = {
            'up': (108, 105, 110, 107, 32, 117, 112, 32, 114, 111, 115, 10),
            'ping': (108, 105, 110, 107, 32, 112, 105, 110, 103, 32, 114, 111, 115, 10),
            'down': (108, 105, 110, 107, 32, 100, 111, 119, 110, 32, 114, 111, 115, 10),
        }
        return ''.join(chr(value) for value in values[state])

    @staticmethod
    def _ignored_response_prefixes():
        return ('FW', 'DIAG', 'LINK', 'OK', 'ERROR')

    def write_raw(self, command):
        failed_conn = None
        with self.serial_lock:
            conn = self.serial_conn
            if conn is None or not conn.is_open:
                return False
            try:
                conn.write(command.encode('utf-8'))
                conn.flush()
                return True
            except SERIAL_ERRORS as exc:
                self.get_logger().warning(f"Serial write failed: {exc}")
                if self.serial_conn is conn:
                    self.serial_conn = None
                failed_conn = conn
        if failed_conn:
            try:
                failed_conn.close()
            except Exception:
                pass
        return False

    def cmd_vel_callback(self, msg):
        speed = self.clamp(msg.linear.x, -self.max_speed, self.max_speed)
        if abs(speed) < 0.01:
            steering = 0.0 if msg.angular.z == 0.0 else math.copysign(self.max_steering_angle, msg.angular.z)
        else:
            steering = math.atan(self.wheelbase * msg.angular.z / speed)
        self.send_drive_command(speed, steering)

    def ackermann_cmd_callback(self, msg):
        self.send_drive_command(msg.speed, msg.steering_angle)

    def send_drive_command(self, speed, steering):
        speed = self.clamp(float(speed), -self.max_speed, self.max_speed)
        steering = self.clamp(float(steering), -self.max_steering_angle, self.max_steering_angle)
        if self.write_raw(f"v {speed:.3f} {math.degrees(steering):.2f}\n"):
            self.last_cmd_time = self.get_clock().now()

    def read_loop(self):
        current_thread = threading.current_thread()
        try:
            while not self.shutdown_event.is_set() and rclpy.ok():
                with self.serial_lock:
                    conn = self.serial_conn
                if conn is None or not conn.is_open:
                    break
                try:
                    line = conn.readline().decode('utf-8', errors='ignore').strip()
                except SERIAL_ERRORS as exc:
                    if self.shutdown_event.is_set():
                        break
                    self.get_logger().warning(f"Serial read failed: {exc}")
                    self.close_serial(conn)
                    break
                if line:
                    self.handle_device_line(line)
        finally:
            with self.serial_lock:
                if self.reader_thread is current_thread:
                    self.reader_thread = None

    def shutdown_driver(self):
        self.shutdown_event.set()
        self.close_serial()
        with self.serial_lock:
            reader = self.reader_thread
        if reader and reader is not threading.current_thread() and reader.is_alive():
            reader.join(timeout=1.0)

    def handle_device_line(self, line):
        parts = line.split()
        if not parts:
            return
        command = parts[0]
        if command.startswith(self._ignored_response_prefixes()) or command == 'link':
            return
        try:
            if command == 's' and len(parts) == 18:
                self.publish_motion_state(parts)
            elif command == 'r':
                self.publish_rc_data(parts)
                if len(parts) >= 8:
                    self.update_control_source(parts)
            elif command == 'm' and len(parts) == 4:
                self.publish_magnetometer(parts)
            elif (
                command == 'b'
                and len(parts) == 2
                and self.publish_battery_enabled
                and self.battery_pub is not None
            ):
                self.publish_battery(float(parts[1]))
        except ValueError as exc:
            self.get_logger().warning(f"Could not parse chassis data: {exc}")

    def publish_rc_data(self, parts):
        if not self.publish_rc_enabled or self.rc_pub is None:
            return
        msg = Int32MultiArray()
        msg.data = [int(value) for value in parts[1:]]
        self.rc_pub.publish(msg)

    def publish_magnetometer(self, parts):
        if not self.publish_mag_enabled or self.mag_pub is None:
            return
        msg = MagneticField()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.mag_frame_id
        msg.magnetic_field.x = float(parts[1]) * 1e-4
        msg.magnetic_field.y = float(parts[2]) * 1e-4
        msg.magnetic_field.z = float(parts[3]) * 1e-4
        self.mag_pub.publish(msg)

    def update_control_source(self, parts):
        control_channel = int(parts[7])
        remote_active = 0 <= control_channel < 1500
        if remote_active == self.remote_control_active:
            return
        self.remote_control_active = remote_active
        if remote_active:
            self.get_logger().warning(
                "Remote control is active; ROS motion commands may be ignored until serial control is selected"
            )
        else:
            self.get_logger().info("Serial control is active")

    def publish_motion_state(self, parts):
        px, py, pz = float(parts[1]), float(parts[2]), float(parts[3])
        vx, vy, vz = float(parts[4]), float(parts[5]), float(parts[6])
        qx, qy, qz, qw = float(parts[8]), float(parts[9]), float(parts[10]), float(parts[11])
        ax, ay, az = float(parts[12]), float(parts[13]), float(parts[14])
        gx, gy, gz = float(parts[15]), float(parts[16]), float(parts[17])

        stamp = self.get_clock().now().to_msg()

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.odom_frame_id
        odom.child_frame_id = self.base_frame_id
        odom.pose.pose.position.x = px
        odom.pose.pose.position.y = py
        odom.pose.pose.position.z = pz
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = vx
        odom.twist.twist.linear.y = vy
        odom.twist.twist.linear.z = vz
        odom.twist.covariance = self.odom_twist_covariance
        self.odom_pub.publish(odom)

        if self.tf_broadcaster:
            transform = TransformStamped()
            transform.header.stamp = stamp
            transform.header.frame_id = self.odom_frame_id
            transform.child_frame_id = self.base_frame_id
            transform.transform.translation.x = px
            transform.transform.translation.y = py
            transform.transform.translation.z = pz
            transform.transform.rotation = odom.pose.pose.orientation
            self.tf_broadcaster.sendTransform(transform)

        imu = Imu()
        imu.header.stamp = stamp
        imu.header.frame_id = self.imu_frame_id
        imu.orientation.x = qx
        imu.orientation.y = qy
        imu.orientation.z = qz
        imu.orientation.w = qw
        imu.linear_acceleration.x = ax
        imu.linear_acceleration.y = ay
        imu.linear_acceleration.z = az
        imu.angular_velocity.x = gx
        imu.angular_velocity.y = gy
        imu.angular_velocity.z = gz
        imu.orientation_covariance = self.imu_orientation_covariance
        imu.angular_velocity_covariance = self.imu_angular_velocity_covariance
        imu.linear_acceleration_covariance = self.imu_linear_acceleration_covariance
        self.imu_pub.publish(imu)

    def publish_battery(self, voltage):
        if not self.publish_battery_enabled or self.battery_pub is None:
            return
        msg = BatteryState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.voltage = voltage
        if self.battery_voltage_max > self.battery_voltage_min:
            pct = (voltage - self.battery_voltage_min) / (self.battery_voltage_max - self.battery_voltage_min)
            msg.percentage = self.clamp(pct, 0.0, 1.0)
        self.battery_pub.publish(msg)

    @staticmethod
    def diagonal_covariance(diagonal):
        if len(diagonal) != 3:
            raise ValueError("IMU covariance parameters must contain exactly 3 diagonal values")
        return [
            float(diagonal[0]), 0.0, 0.0,
            0.0, float(diagonal[1]), 0.0,
            0.0, 0.0, float(diagonal[2]),
        ]

    @staticmethod
    def diagonal_covariance_6d(diagonal):
        if len(diagonal) != 6:
            raise ValueError("Odometry twist covariance parameter must contain exactly 6 diagonal values")
        covariance = [0.0] * 36
        for index, value in enumerate(diagonal):
            covariance[index * 6 + index] = float(value)
        return covariance

    def watchdog_check(self):
        if self.shutdown_event.is_set():
            return
        elapsed = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9
        if elapsed > self.cmd_timeout:
            self.write_raw("v 0.00 0.00\n")

    @staticmethod
    def clamp(value, lower, upper):
        return max(lower, min(upper, value))

    def resolve_max_speed(self, max_speed, speed_mode):
        speed = abs(float(max_speed))
        mode = str(speed_mode).strip().lower()
        if mode == 'low':
            return speed * LOW_SPEED_RATIO
        if mode != 'high':
            self.get_logger().warning(f"Unknown speed_mode '{speed_mode}', using high")
        return speed

    @staticmethod
    def as_bool(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def main(args=None):
    rclpy.init(args=args)
    node = ChassisDriver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.shutdown_driver()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
