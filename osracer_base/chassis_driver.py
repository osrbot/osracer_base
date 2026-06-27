import math
import os
import re
import threading
import time

import rospy
import serial
from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState, Imu
from tf2_ros import TransformBroadcaster


MAX_ALLOWED_SPEED = 1.5
LOW_SPEED_RATIO = 0.15


class ChassisDriver:
    def __init__(self):
        rospy.init_node('osracer_base')

        self.port = rospy.get_param('~port', '/dev/osrbot_base')
        self.baudrate = int(rospy.get_param('~baudrate', 460800))
        self.wheelbase = float(rospy.get_param('~wheelbase', 0.325))
        self.max_speed = self.resolve_max_speed(
            rospy.get_param('~max_speed', MAX_ALLOWED_SPEED),
            rospy.get_param('~speed_mode', 'high'),
        )
        self.max_steering_angle = abs(float(rospy.get_param('~max_steering_angle', math.radians(30.0))))
        self.cmd_timeout = float(rospy.get_param('~cmd_timeout', 0.5))
        self.reconnect_interval = float(rospy.get_param('~reconnect_interval', 2.0))
        self.firmware_version_timeout = float(rospy.get_param('~firmware_version_timeout', 0.5))
        self.connection_status_enabled = self.as_bool(rospy.get_param('~connection_status_enabled', True))
        self.connection_refresh_period = float(rospy.get_param('~connection_refresh_period', 1.0))
        self.odom_frame_id = rospy.get_param('~odom_frame_id', 'odom')
        self.base_frame_id = rospy.get_param('~base_frame_id', 'base_footprint')
        self.imu_frame_id = rospy.get_param('~imu_frame_id', 'imu_link')
        self.publish_tf = self.as_bool(rospy.get_param('~publish_tf', True))
        self.battery_voltage_min = float(rospy.get_param('~battery_voltage_min', 10.8))
        self.battery_voltage_max = float(rospy.get_param('~battery_voltage_max', 12.6))

        rospy.Subscriber('cmd_vel', Twist, self.cmd_vel_callback, queue_size=5)
        rospy.Subscriber('ackermann_cmd', AckermannDriveStamped, self.ackermann_cmd_callback, queue_size=5)
        self.odom_pub = rospy.Publisher('odom', Odometry, queue_size=1)
        self.imu_pub = rospy.Publisher('imu/data', Imu, queue_size=1)
        self.battery_pub = rospy.Publisher('battery_state', BatteryState, queue_size=5)
        self.tf_broadcaster = TransformBroadcaster() if self.publish_tf else None

        self.serial_conn = None
        self.serial_lock = threading.Lock()
        self.reader_thread = None
        self.last_cmd_time = rospy.Time.now()
        self.remote_control_active = None

        rospy.Timer(rospy.Duration(self.reconnect_interval), self.ensure_connected)
        rospy.Timer(rospy.Duration(0.1), self.watchdog_check)
        rospy.Timer(
            rospy.Duration(max(0.2, self.connection_refresh_period)),
            self.refresh_connection_status,
        )
        rospy.on_shutdown(self.close_serial)

        rospy.loginfo("ROS speed limit: %.3f m/s", self.max_speed)
        self.ensure_connected()

    def ensure_connected(self, event=None):
        with self.serial_lock:
            connected = self.serial_conn is not None and self.serial_conn.is_open
        if connected:
            self.start_reader()
            return

        if self.port.startswith('/') and not os.path.exists(self.port):
            rospy.logwarn("Serial device not found: %s", self.port)
            return

        try:
            conn = serial.Serial(self.port, self.baudrate, timeout=0.1, write_timeout=0.1)
            conn.reset_input_buffer()
            conn.reset_output_buffer()
        except (serial.SerialException, OSError, ValueError) as exc:
            rospy.logwarn("Could not open serial device %s: %s", self.port, exc)
            return

        with self.serial_lock:
            self.serial_conn = conn
        self.configure_device()
        self.start_reader()
        rospy.loginfo("Connected to chassis on %s", self.port)

    def configure_device(self):
        self.log_firmware_version()
        self.write_raw(self._device_mode_command())
        self.write_raw(self._state_request_command())
        self.send_connection_status('up')

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

    def log_firmware_version(self):
        with self.serial_lock:
            conn = self.serial_conn
            if conn is None or not conn.is_open:
                return
            try:
                conn.reset_input_buffer()
                conn.write(self._quiet_command().encode('utf-8'))
                conn.flush()
                time.sleep(0.05)
                conn.reset_input_buffer()
                conn.write(self._version_command().encode('utf-8'))
                conn.flush()
            except (serial.SerialException, OSError, ValueError) as exc:
                rospy.logwarn("Could not query chassis firmware version: %s", exc)
                return

        deadline = time.monotonic() + max(0.1, self.firmware_version_timeout)
        while time.monotonic() < deadline and not rospy.is_shutdown():
            with self.serial_lock:
                conn = self.serial_conn
                if conn is None or not conn.is_open:
                    return
                try:
                    line = conn.readline().decode('utf-8', errors='ignore').strip()
                except (serial.SerialException, OSError, ValueError) as exc:
                    rospy.logwarn("Could not read chassis firmware version: %s", exc)
                    return
            if not line:
                continue
            project_ver = self.parse_project_version(line)
            if project_ver:
                rospy.loginfo("Chassis firmware ProjectVer: %s", project_ver)
                return

        rospy.logwarn("Chassis firmware version unavailable")

    @staticmethod
    def parse_project_version(line):
        match = re.search(r'\bProjectVer\s*[:=]\s*([^,\s]+)', line)
        if match:
            return match.group(1)
        match = re.search(r'\bProjectVer\s+([^,\s]+)', line)
        if match:
            return match.group(1)
        return None

    def start_reader(self):
        if self.reader_thread and self.reader_thread.is_alive():
            return
        self.reader_thread = threading.Thread(target=self.read_loop)
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def close_serial(self):
        with self.serial_lock:
            conn = self.serial_conn
            self.serial_conn = None
        if conn:
            try:
                if conn.is_open:
                    self.write_connection_down(conn)
                conn.close()
            except (serial.SerialException, OSError):
                pass

    def send_connection_status(self, state):
        if not self.connection_status_enabled:
            return True
        return self.write_raw(self._connection_status_command(state))

    def refresh_connection_status(self, event=None):
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
        except (serial.SerialException, OSError, ValueError):
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
        values = (
            (79, 75, 58),
            (69, 82, 82, 79, 82, 58),
            (70, 87, 58),
            (68, 73, 65, 71, 58),
        )
        return tuple(''.join(chr(value) for value in item) for item in values)

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
            except (serial.SerialException, OSError, ValueError) as exc:
                rospy.logwarn("Serial write failed: %s", exc)
                failed_conn = conn
                self.serial_conn = None
        if failed_conn:
            try:
                failed_conn.close()
            except (serial.SerialException, OSError):
                pass
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
            self.last_cmd_time = rospy.Time.now()

    def read_loop(self):
        current_thread = threading.current_thread()
        try:
            while not rospy.is_shutdown():
                with self.serial_lock:
                    conn = self.serial_conn
                if conn is None or not conn.is_open:
                    break
                try:
                    line = conn.readline().decode('utf-8', errors='ignore').strip()
                except (serial.SerialException, OSError, ValueError) as exc:
                    rospy.logwarn("Serial read failed: %s", exc)
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
            elif parts[0] == 'r' and len(parts) >= 8:
                self.update_control_source(parts)
            elif parts[0] in self._ignored_response_prefixes():
                return
        except ValueError as exc:
            rospy.logwarn("Could not parse chassis data: %s", exc)

    def update_control_source(self, parts):
        control_channel = int(parts[7])
        remote_active = 0 <= control_channel < 1500
        if remote_active == self.remote_control_active:
            return
        self.remote_control_active = remote_active
        if remote_active:
            rospy.logwarn("Remote control is active; ROS motion commands may be ignored until serial control is selected")
        else:
            rospy.loginfo("Serial control is active")

    def publish_motion_state(self, parts):
        px, py, pz = float(parts[1]), float(parts[2]), float(parts[3])
        vx, vy, vz = float(parts[4]), float(parts[5]), float(parts[6])
        qx, qy, qz, qw = float(parts[8]), float(parts[9]), float(parts[10]), float(parts[11])
        ax, ay, az = float(parts[12]), float(parts[13]), float(parts[14])
        gx, gy, gz = float(parts[15]), float(parts[16]), float(parts[17])

        stamp = rospy.Time.now()

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
        msg.header.stamp = rospy.Time.now()
        msg.voltage = voltage
        if self.battery_voltage_max > self.battery_voltage_min:
            pct = (voltage - self.battery_voltage_min) / (self.battery_voltage_max - self.battery_voltage_min)
            msg.percentage = self.clamp(pct, 0.0, 1.0)
        self.battery_pub.publish(msg)

    def watchdog_check(self, event=None):
        elapsed = (rospy.Time.now() - self.last_cmd_time).to_sec()
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

    def resolve_max_speed(self, max_speed, speed_mode):
        speed = min(abs(float(max_speed)), MAX_ALLOWED_SPEED)
        mode = str(speed_mode).strip().lower()
        if mode == 'low':
            return speed * LOW_SPEED_RATIO
        if mode != 'high':
            rospy.logwarn("Unknown speed_mode '%s', using high", speed_mode)
        return speed


def main():
    ChassisDriver()
    rospy.spin()


if __name__ == '__main__':
    main()
