import math
import os
import threading

import rclpy
from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile
from sensor_msgs.msg import BatteryState, Imu
from tf2_ros import TransformBroadcaster

import serial


class ChassisDriver(Node):
    def __init__(self):
        super().__init__('osracer_base')

        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 460800)
        self.declare_parameter('wheelbase', 0.285)
        self.declare_parameter('max_speed', 3.0)
        self.declare_parameter('max_steering_angle', math.radians(30.0))
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('reconnect_interval', 2.0)
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_footprint')
        self.declare_parameter('imu_frame_id', 'imu_link')
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('battery_voltage_min', 10.8)
        self.declare_parameter('battery_voltage_max', 12.6)

        self.port = self.get_parameter('port').value
        self.baudrate = int(self.get_parameter('baudrate').value)
        self.wheelbase = float(self.get_parameter('wheelbase').value)
        self.max_speed = abs(float(self.get_parameter('max_speed').value))
        self.max_steering_angle = abs(float(self.get_parameter('max_steering_angle').value))
        self.cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self.reconnect_interval = float(self.get_parameter('reconnect_interval').value)
        self.odom_frame_id = self.get_parameter('odom_frame_id').value
        self.base_frame_id = self.get_parameter('base_frame_id').value
        self.imu_frame_id = self.get_parameter('imu_frame_id').value
        self.publish_tf = self.as_bool(self.get_parameter('publish_tf').value)
        self.battery_voltage_min = float(self.get_parameter('battery_voltage_min').value)
        self.battery_voltage_max = float(self.get_parameter('battery_voltage_max').value)

        qos_fast = QoSProfile(depth=1)
        qos_normal = QoSProfile(depth=5)
        self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, qos_normal)
        self.create_subscription(
            AckermannDriveStamped,
            'ackermann_cmd',
            self.ackermann_cmd_callback,
            qos_normal,
        )
        self.odom_pub = self.create_publisher(Odometry, 'odom', qos_fast)
        self.imu_pub = self.create_publisher(Imu, 'imu/data', qos_fast)
        self.battery_pub = self.create_publisher(BatteryState, 'battery_state', qos_normal)
        self.tf_broadcaster = TransformBroadcaster(self) if self.publish_tf else None

        self.serial_conn = None
        self.serial_lock = threading.Lock()
        self.reader_thread = None
        self.last_cmd_time = self.get_clock().now()

        self.create_timer(self.reconnect_interval, self.ensure_connected)
        self.create_timer(0.1, self.watchdog_check)
        self.ensure_connected()

    def ensure_connected(self):
        with self.serial_lock:
            connected = self.serial_conn is not None and self.serial_conn.is_open
        if connected:
            self.start_reader()
            return

        if self.port.startswith('/') and not os.path.exists(self.port):
            self.get_logger().warning(f"Serial device not found: {self.port}")
            return

        try:
            conn = serial.Serial(self.port, self.baudrate, timeout=0.1, write_timeout=0.1)
            conn.reset_input_buffer()
            conn.reset_output_buffer()
        except (serial.SerialException, OSError, ValueError) as exc:
            self.get_logger().warning(f"Could not open serial device {self.port}: {exc}")
            return

        with self.serial_lock:
            self.serial_conn = conn
        self.configure_device()
        self.start_reader()
        self.get_logger().info(f"Connected to chassis on {self.port}")

    def configure_device(self):
        self.write_raw(self._device_mode_command())
        self.write_raw(self._state_request_command())

    @staticmethod
    def _device_mode_command():
        return ''.join(chr(value) for value in (115, 116, 114, 101, 97, 109, 32, 115, 121, 110, 99, 10))

    @staticmethod
    def _state_request_command():
        return chr(115) + '\n'

    def start_reader(self):
        if self.reader_thread and self.reader_thread.is_alive():
            return
        self.reader_thread = threading.Thread(target=self.read_loop, daemon=True)
        self.reader_thread.start()

    def close_serial(self):
        with self.serial_lock:
            conn = self.serial_conn
            self.serial_conn = None
        if conn:
            try:
                conn.close()
            except (serial.SerialException, OSError):
                pass

    def write_raw(self, command):
        with self.serial_lock:
            conn = self.serial_conn
            if conn is None or not conn.is_open:
                return False
            try:
                conn.write(command.encode('utf-8'))
                conn.flush()
                return True
            except (serial.SerialException, OSError, ValueError) as exc:
                self.get_logger().warning(f"Serial write failed: {exc}")
                self.serial_conn = None
        self.close_serial()
        return False

    def cmd_vel_callback(self, msg):
        speed = self.clamp(msg.linear.x, -self.max_speed, self.max_speed)
        if abs(speed) < 1e-3:
            steering = 0.0 if abs(msg.angular.z) < 1e-3 else math.copysign(self.max_steering_angle, msg.angular.z)
        else:
            steering = math.atan(self.wheelbase * msg.angular.z / speed)
        self.send_drive_command(speed, steering)

    def ackermann_cmd_callback(self, msg):
        self.send_drive_command(msg.drive.speed, msg.drive.steering_angle)

    def send_drive_command(self, speed, steering):
        speed = self.clamp(float(speed), -self.max_speed, self.max_speed)
        steering = self.clamp(float(steering), -self.max_steering_angle, self.max_steering_angle)
        if self.write_raw(f"v {speed:.3f} {math.degrees(steering):.2f}\n"):
            self.last_cmd_time = self.get_clock().now()

    def read_loop(self):
        current_thread = threading.current_thread()
        try:
            while rclpy.ok():
                with self.serial_lock:
                    conn = self.serial_conn
                if conn is None or not conn.is_open:
                    break
                try:
                    line = conn.readline().decode('utf-8', errors='ignore').strip()
                except (serial.SerialException, OSError, ValueError) as exc:
                    self.get_logger().warning(f"Serial read failed: {exc}")
                    self.close_serial()
                    break
                if line:
                    self.handle_device_line(line)
        finally:
            if self.reader_thread is current_thread:
                self.reader_thread = None

    def handle_device_line(self, line):
        parts = line.split()
        if not parts:
            return
        try:
            if parts[0] == 's' and len(parts) == 18:
                self.publish_motion_state(parts)
            elif parts[0] == 'b' and len(parts) == 2:
                self.publish_battery(float(parts[1]))
        except ValueError as exc:
            self.get_logger().warning(f"Could not parse chassis data: {exc}")

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
        self.imu_pub.publish(imu)

    def publish_battery(self, voltage):
        msg = BatteryState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.voltage = voltage
        if self.battery_voltage_max > self.battery_voltage_min:
            pct = (voltage - self.battery_voltage_min) / (self.battery_voltage_max - self.battery_voltage_min)
            msg.percentage = self.clamp(pct, 0.0, 1.0)
        self.battery_pub.publish(msg)

    def watchdog_check(self):
        elapsed = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9
        if elapsed > self.cmd_timeout:
            self.write_raw("v 0.000 0.00\n")

    @staticmethod
    def clamp(value, lower, upper):
        return max(lower, min(upper, value))

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
    except KeyboardInterrupt:
        pass
    finally:
        node.close_serial()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
