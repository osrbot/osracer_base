import importlib.util
import json
import math
import re
import signal
import sys
import threading
import types
import unittest
from collections import deque
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
DRIVER_PATH = REPO_ROOT / 'osracer_base' / 'chassis_driver.py'
FIXTURE_PATH = REPO_ROOT / 'test' / 'fixtures' / 'proto_1_1' / 'session.json'
WORKFLOW_PATH = REPO_ROOT / '.github' / 'workflows' / 'ros2-ci.yml'


class _Vector:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0


class _Quaternion(_Vector):
    def __init__(self):
        super().__init__()
        self.w = 0.0


class _Header:
    def __init__(self):
        self.stamp = None
        self.frame_id = ''


class _Twist:
    def __init__(self):
        self.linear = _Vector()
        self.angular = _Vector()


class _AckermannDrive:
    def __init__(self):
        self.speed = 0.0
        self.steering_angle = 0.0


class _Odometry:
    def __init__(self):
        self.header = _Header()
        self.child_frame_id = ''
        self.pose = types.SimpleNamespace(
            pose=types.SimpleNamespace(position=_Vector(), orientation=_Quaternion())
        )
        self.twist = types.SimpleNamespace(twist=_Twist(), covariance=[0.0] * 36)


class _Imu:
    def __init__(self):
        self.header = _Header()
        self.orientation = _Quaternion()
        self.angular_velocity = _Vector()
        self.linear_acceleration = _Vector()
        self.orientation_covariance = [0.0] * 9
        self.angular_velocity_covariance = [0.0] * 9
        self.linear_acceleration_covariance = [0.0] * 9


class _MagneticField:
    def __init__(self):
        self.header = _Header()
        self.magnetic_field = _Vector()


class _BatteryState:
    def __init__(self):
        self.header = _Header()
        self.voltage = 0.0
        self.percentage = 0.0


class _Int32MultiArray:
    def __init__(self):
        self.data = []


class _TransformStamped:
    def __init__(self):
        self.header = _Header()
        self.child_frame_id = ''
        self.transform = types.SimpleNamespace(translation=_Vector(), rotation=_Quaternion())


class _SerialException(Exception):
    pass


class _ExternalShutdownException(Exception):
    pass


class _Logger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, message):
        self.infos.append(str(message))

    def warning(self, message):
        self.warnings.append(str(message))


class _Delta:
    def __init__(self, nanoseconds):
        self.nanoseconds = nanoseconds


class _TimePoint:
    def __init__(self, nanoseconds):
        self.nanoseconds = nanoseconds

    def __sub__(self, other):
        return _Delta(self.nanoseconds - other.nanoseconds)

    def to_msg(self):
        return self.nanoseconds


class _Clock:
    def __init__(self, nanoseconds=0):
        self.nanoseconds = nanoseconds

    def now(self):
        return _TimePoint(self.nanoseconds)


class _FakeSerial:
    def __init__(self, version_line=None, fail_on_write=None):
        self.is_open = True
        self.version_line = version_line
        self.fail_on_write = fail_on_write
        self.lines = deque()
        self.writes = []
        self.close_count = 0

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass

    def write(self, payload):
        text = payload.decode('utf-8')
        if text == self.fail_on_write:
            raise _SerialException('synthetic write failure')
        self.writes.append(text)
        if text == 'fw version\n' and self.version_line:
            self.lines.append((self.version_line + '\n').encode('utf-8'))
        return len(payload)

    def flush(self):
        pass

    def readline(self):
        return self.lines.popleft() if self.lines else b''

    def close(self):
        self.close_count += 1
        self.is_open = False


def _module(name, **attributes):
    result = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(result, key, value)
    return result


def _load_driver_module():
    class _Node:
        pass

    class _QoSProfile:
        def __init__(self, depth):
            self.depth = depth

    class _Message:
        pass

    class _TransformBroadcaster:
        def __init__(self, node):
            self.node = node

    rclpy = _module('rclpy', ok=lambda: True)
    stubs = {
        'rclpy': rclpy,
        'rclpy.executors': _module(
            'rclpy.executors',
            ExternalShutdownException=_ExternalShutdownException,
        ),
        'rclpy.node': _module('rclpy.node', Node=_Node),
        'rclpy.qos': _module('rclpy.qos', QoSProfile=_QoSProfile),
        'ackermann_msgs': _module('ackermann_msgs'),
        'ackermann_msgs.msg': _module(
            'ackermann_msgs.msg',
            AckermannDrive=_AckermannDrive,
        ),
        'geometry_msgs': _module('geometry_msgs'),
        'geometry_msgs.msg': _module(
            'geometry_msgs.msg',
            TransformStamped=_TransformStamped,
            Twist=_Twist,
        ),
        'nav_msgs': _module('nav_msgs'),
        'nav_msgs.msg': _module('nav_msgs.msg', Odometry=_Odometry),
        'sensor_msgs': _module('sensor_msgs'),
        'sensor_msgs.msg': _module(
            'sensor_msgs.msg',
            BatteryState=_BatteryState,
            Imu=_Imu,
            MagneticField=_MagneticField,
        ),
        'std_msgs': _module('std_msgs'),
        'std_msgs.msg': _module('std_msgs.msg', Int32MultiArray=_Int32MultiArray),
        'tf2_ros': _module('tf2_ros', TransformBroadcaster=_TransformBroadcaster),
        'serial': _module(
            'serial',
            Serial=lambda *args, **kwargs: None,
            SerialException=_SerialException,
        ),
    }
    with mock.patch.dict(sys.modules, stubs):
        spec = importlib.util.spec_from_file_location('chassis_driver_under_test', DRIVER_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


DRIVER = _load_driver_module()


def _fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))


def _driver_shell():
    driver = object.__new__(DRIVER.ChassisDriver)
    driver.serial_lock = threading.Lock()
    driver.serial_conn = None
    driver.reader_thread = None
    driver.shutdown_event = threading.Event()
    driver.port = 'loop://sanitized'
    driver.baudrate = 460800
    driver.firmware_version_timeout = 0.01
    driver.connection_status_enabled = True
    driver.remote_control_active = None
    driver.publish_rc_enabled = True
    driver.publish_mag_enabled = True
    driver.publish_battery_enabled = True
    driver.rc_pub = mock.Mock()
    driver.mag_pub = mock.Mock()
    driver.battery_pub = mock.Mock()
    driver.logger = _Logger()
    driver.get_logger = lambda: driver.logger
    driver.start_reader = mock.Mock()
    return driver


class FixtureContractTests(unittest.TestCase):
    def test_fixture_is_sanitized_and_proto_1_1(self):
        data = _fixture()
        text = FIXTURE_PATH.read_text(encoding='utf-8')

        self.assertEqual(data['protocol'], '1.1')
        self.assertEqual(
            data['behavior_baseline'],
            {
                'repository': 'osrbot/osracer',
                'commit': 'c329c21614f0335d9a8c7a12d2e638a70293052f',
            },
        )
        self.assertFalse(data['sanitization']['private_source_copied'])
        self.assertTrue(data['sanitization']['identifiers_removed'])
        self.assertTrue(data['sanitization']['telemetry_values_synthetic'])
        self.assertFalse(data['sanitization']['vehicle_profile_values_included'])
        self.assertNotRegex(text, re.compile(r'\b[0-9A-F]{12}\b'))
        for forbidden in ('NEORACER', 'OSRCOREV', 'T005', 'customer', 'serial_number'):
            self.assertNotIn(forbidden, text)

    def test_fixture_records_startup_and_watchdog_contract(self):
        data = _fixture()
        self.assertEqual(
            data['startup']['expected_host_commands'],
            [
                'stream off\n',
                'fw version\n',
                'stream sync\n',
                's\n',
                'link up ros\n',
            ],
        )
        self.assertEqual(data['control']['watchdog_seconds'], 0.5)
        self.assertEqual(data['control']['watchdog_command'], 'v 0.00 0.00\n')
        self.assertEqual(data['control']['cmd_vel_near_zero_mps'], 0.01)
        self.assertEqual(data['startup']['firmware_version_timeout_seconds'], 0.3)

    def test_fixture_records_c329_sensor_contract(self):
        data = _fixture()
        self.assertEqual(data['publishers']['rc_topic'], 'rc_data')
        self.assertEqual(data['publishers']['mag_topic'], 'magnetometer_data')
        self.assertEqual(data['publishers']['mag_frame_id'], 'imu_link')
        self.assertEqual(data['publishers']['battery_topic'], 'battery_state')
        self.assertEqual(data['publishers']['gauss_to_tesla'], 1e-4)
        self.assertEqual(data['covariance_diagonals']['imu_orientation'], [0.02, 0.02, 0.05])
        self.assertEqual(data['covariance_diagonals']['odom_twist'], [0.02, 0.20, 1.0, 1.0, 1.0, 0.30])


class PublicApiTests(unittest.TestCase):
    def test_ackermann_cmd_uses_unstamped_message(self):
        source = DRIVER_PATH.read_text(encoding='utf-8')
        self.assertIs(DRIVER.AckermannDrive, _AckermannDrive)
        self.assertNotIn('AckermannDriveStamped', source)

    def test_base_uses_one_canonical_parameter_api(self):
        source = DRIVER_PATH.read_text(encoding='utf-8')
        launch = (REPO_ROOT / 'launch' / 'chassis_driver.launch.py').read_text(encoding='utf-8')
        odom_view_launch = (REPO_ROOT / 'launch' / 'odom_view.launch.py').read_text(encoding='utf-8')
        for name in (
            'publish_rc', 'rc_topic', 'publish_mag', 'mag_topic', 'mag_frame_id',
            'imu_orientation_covariance', 'imu_angular_velocity_covariance',
            'imu_linear_acceleration_covariance', 'odom_twist_covariance',
            'publish_battery', 'battery_topic',
        ):
            self.assertIn(f"declare_parameter('{name}'", source)
            self.assertIn(f"DeclareLaunchArgument('{name}'", launch)
            self.assertIn(f"DeclareLaunchArgument('{name}'", odom_view_launch)
        for legacy_name in (
            'port_name', 'baud_rate', 'odom_frame', 'base_frame', 'imu_frame',
            'max_steering_angle_deg', 'cmd_watchdog_timeout_s', 'reconnect_interval_s',
            'firmware_version_timeout_s', 'link_status_enabled', 'link_ping_period_s',
        ):
            self.assertNotIn(f"declare_parameter('{legacy_name}'", source)
            self.assertNotIn(f"DeclareLaunchArgument('{legacy_name}'", launch)
        self.assertIn('ParameterValue(', launch)
        self.assertEqual(launch.count('value_type=list[float]'), 4)
        self.assertIn("declare_parameter('firmware_version_timeout', 0.3)", source)
        self.assertIn("DeclareLaunchArgument('firmware_version_timeout', default_value='0.3')", launch)
        package_xml = (REPO_ROOT / 'package.xml').read_text(encoding='utf-8')
        self.assertIn('<depend>std_msgs</depend>', package_xml)

    def test_readmes_document_c329_to_base_parameter_mapping(self):
        for filename in ('README.md', 'README_zh.md'):
            text = (REPO_ROOT / filename).read_text(encoding='utf-8')
            for legacy, canonical in (
                ('port_name', 'port'),
                ('baud_rate', 'baudrate'),
                ('odom_frame', 'odom_frame_id'),
                ('base_frame', 'base_frame_id'),
                ('imu_frame', 'imu_frame_id'),
                ('max_steering_angle_deg', 'max_steering_angle'),
                ('cmd_watchdog_timeout_s', 'cmd_timeout'),
                ('reconnect_interval_s', 'reconnect_interval'),
                ('firmware_version_timeout_s', 'firmware_version_timeout'),
                ('link_status_enabled', 'connection_status_enabled'),
                ('link_ping_period_s', 'connection_refresh_period'),
                ('mag_frame', 'mag_frame_id'),
            ):
                self.assertRegex(text, rf'`{legacy}`\s*\|\s*`{canonical}`')


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.driver = _driver_shell()
        self.driver.publish_motion_state = mock.Mock()
        self.driver.publish_battery = mock.Mock()
        self.driver.publish_rc_data = mock.Mock()
        self.driver.publish_magnetometer = mock.Mock()
        self.driver.update_control_source = mock.Mock()
        self.data = _fixture()

    def test_dispatches_sanitized_proto_frames(self):
        telemetry = self.data['telemetry']
        self.driver.handle_device_line(telemetry['sync'])
        self.driver.handle_device_line(telemetry['battery'])
        self.driver.handle_device_line(telemetry['remote'])
        self.driver.handle_device_line(telemetry['magnetometer'])

        self.driver.publish_motion_state.assert_called_once()
        self.driver.publish_battery.assert_called_once_with(12.10)
        self.driver.publish_rc_data.assert_called_once()
        self.driver.publish_magnetometer.assert_called_once()
        self.driver.update_control_source.assert_called_once()

    def test_ignores_unknown_and_non_baseline_frames(self):
        for line in self.data['telemetry']['ignored_responses']:
            self.driver.handle_device_line(line)
        for index in (0, 1, 3):
            self.driver.handle_device_line(self.data['malformed'][index])

        self.driver.publish_motion_state.assert_not_called()
        self.driver.publish_battery.assert_not_called()
        self.driver.publish_rc_data.assert_not_called()
        self.driver.publish_magnetometer.assert_not_called()
        self.driver.update_control_source.assert_not_called()

    def test_bad_battery_value_is_logged_without_raising(self):
        self.driver.handle_device_line(self.data['malformed'][2])
        self.assertEqual(len(self.driver.logger.warnings), 1)

    def test_project_version_parser_accepts_proto_1_1_fixture(self):
        line = self.data['startup']['firmware_version_response']
        self.assertEqual(DRIVER.ChassisDriver.parse_project_version(line), 'PUBLIC_TEST_FIXTURE')

    def test_c329_response_prefixes_are_ignored(self):
        for line in ('FW_VERSION: synthetic', 'LINK: synthetic', 'ERROR_DETAIL: synthetic', 'link pong ros'):
            self.driver.handle_device_line(line)
        self.assertEqual(self.driver.logger.warnings, [])
        self.driver.publish_motion_state.assert_not_called()
        self.driver.publish_rc_data.assert_not_called()


class SensorPublicationTests(unittest.TestCase):
    def setUp(self):
        self.driver = _driver_shell()
        self.driver.clock = _Clock(123)
        self.driver.get_clock = lambda: self.driver.clock
        self.data = _fixture()

    def test_rc_frame_publishes_all_channels(self):
        self.driver.publish_rc_enabled = True
        self.driver.rc_pub = mock.Mock()
        parts = self.data['telemetry']['remote'].split()

        self.driver.publish_rc_data(parts)

        message = self.driver.rc_pub.publish.call_args.args[0]
        self.assertEqual(message.data, [int(value) for value in parts[1:]])

    def test_disabled_rc_publication_keeps_publisher_quiet(self):
        self.driver.publish_rc_enabled = False
        self.driver.rc_pub = mock.Mock()

        self.driver.publish_rc_data(self.data['telemetry']['remote'].split())

        self.driver.rc_pub.publish.assert_not_called()

    def test_magnetometer_converts_gauss_to_tesla(self):
        self.driver.publish_mag_enabled = True
        self.driver.mag_frame_id = 'imu_link'
        self.driver.mag_pub = mock.Mock()

        self.driver.publish_magnetometer(self.data['telemetry']['magnetometer'].split())

        message = self.driver.mag_pub.publish.call_args.args[0]
        self.assertEqual(message.header.stamp, 123)
        self.assertEqual(message.header.frame_id, 'imu_link')
        self.assertAlmostEqual(message.magnetic_field.x, 0.25e-4)
        self.assertAlmostEqual(message.magnetic_field.y, -0.5e-4)
        self.assertAlmostEqual(message.magnetic_field.z, 1.0e-4)

    def test_motion_messages_include_c329_covariances(self):
        covariance = self.data['covariance_diagonals']
        self.driver.odom_frame_id = 'odom'
        self.driver.base_frame_id = 'base_footprint'
        self.driver.imu_frame_id = 'imu_link'
        self.driver.tf_broadcaster = None
        self.driver.odom_pub = mock.Mock()
        self.driver.imu_pub = mock.Mock()
        self.driver.odom_twist_covariance = DRIVER.ChassisDriver.diagonal_covariance_6d(
            covariance['odom_twist']
        )
        self.driver.imu_orientation_covariance = DRIVER.ChassisDriver.diagonal_covariance(
            covariance['imu_orientation']
        )
        self.driver.imu_angular_velocity_covariance = DRIVER.ChassisDriver.diagonal_covariance(
            covariance['imu_angular_velocity']
        )
        self.driver.imu_linear_acceleration_covariance = DRIVER.ChassisDriver.diagonal_covariance(
            covariance['imu_linear_acceleration']
        )

        self.driver.publish_motion_state(self.data['telemetry']['sync'].split())

        odom = self.driver.odom_pub.publish.call_args.args[0]
        imu = self.driver.imu_pub.publish.call_args.args[0]
        self.assertEqual(odom.twist.covariance, self.driver.odom_twist_covariance)
        self.assertEqual(imu.orientation_covariance, self.driver.imu_orientation_covariance)
        self.assertEqual(imu.angular_velocity_covariance, self.driver.imu_angular_velocity_covariance)
        self.assertEqual(imu.linear_acceleration_covariance, self.driver.imu_linear_acceleration_covariance)

    def test_covariance_helpers_reject_wrong_lengths(self):
        with self.assertRaisesRegex(ValueError, 'exactly 3'):
            DRIVER.ChassisDriver.diagonal_covariance([1.0, 2.0])
        with self.assertRaisesRegex(ValueError, 'exactly 6'):
            DRIVER.ChassisDriver.diagonal_covariance_6d([1.0] * 5)

    def test_battery_publish_switch_is_honored_by_parser(self):
        self.driver.publish_motion_state = mock.Mock()
        self.driver.publish_rc_data = mock.Mock()
        self.driver.publish_magnetometer = mock.Mock()
        self.driver.update_control_source = mock.Mock()
        self.driver.publish_battery = mock.Mock()
        self.driver.publish_battery_enabled = False
        self.driver.battery_pub = None

        self.driver.handle_device_line(self.data['telemetry']['battery'])

        self.driver.publish_battery.assert_not_called()

    def test_battery_message_uses_configured_voltage_range(self):
        self.driver.publish_battery_enabled = True
        self.driver.battery_pub = mock.Mock()
        self.driver.battery_voltage_min = 10.8
        self.driver.battery_voltage_max = 12.6

        self.driver.publish_battery(12.1)

        message = self.driver.battery_pub.publish.call_args.args[0]
        self.assertEqual(message.header.stamp, 123)
        self.assertEqual(message.voltage, 12.1)
        self.assertAlmostEqual(message.percentage, (12.1 - 10.8) / (12.6 - 10.8))

    def test_invalid_battery_range_does_not_divide_by_zero(self):
        self.driver.publish_battery_enabled = True
        self.driver.battery_pub = mock.Mock()
        self.driver.battery_voltage_min = 12.0
        self.driver.battery_voltage_max = 12.0

        self.driver.publish_battery(12.0)

        message = self.driver.battery_pub.publish.call_args.args[0]
        self.assertEqual(message.percentage, 0.0)


class ConnectionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.driver = _driver_shell()
        self.data = _fixture()

    def test_startup_sequence_matches_fixture(self):
        serial_conn = _FakeSerial(self.data['startup']['firmware_version_response'])
        with mock.patch.object(DRIVER.serial, 'Serial', return_value=serial_conn), mock.patch.object(
            DRIVER.time, 'sleep', return_value=None
        ):
            self.driver.ensure_connected()

        self.assertEqual(serial_conn.writes, self.data['startup']['expected_host_commands'])
        self.driver.start_reader.assert_called_once_with()
        self.assertTrue(any(message.startswith('Connected to chassis') for message in self.driver.logger.infos))

    def test_failed_initialization_closes_connection_and_does_not_start_reader(self):
        for failed_command in ('stream sync\n', 's\n'):
            with self.subTest(failed_command=failed_command):
                driver = _driver_shell()
                serial_conn = _FakeSerial(
                    self.data['startup']['firmware_version_response'],
                    fail_on_write=failed_command,
                )
                with mock.patch.object(DRIVER.serial, 'Serial', return_value=serial_conn), mock.patch.object(
                    DRIVER.time, 'sleep', return_value=None
                ):
                    driver.ensure_connected()

                self.assertIsNone(driver.serial_conn)
                self.assertFalse(serial_conn.is_open)
                self.assertEqual(serial_conn.close_count, 1)
                driver.start_reader.assert_not_called()
                self.assertFalse(any(message.startswith('Connected to chassis') for message in driver.logger.infos))

    def test_firmware_version_query_failure_does_not_block_connection(self):
        serial_conn = _FakeSerial(fail_on_write='stream off\n')
        with mock.patch.object(DRIVER.serial, 'Serial', return_value=serial_conn), mock.patch.object(
            DRIVER.time, 'sleep', return_value=None
        ):
            self.driver.ensure_connected()

        self.assertEqual(serial_conn.writes, ['stream sync\n', 's\n', 'link up ros\n'])
        self.assertTrue(serial_conn.is_open)
        self.driver.start_reader.assert_called_once_with()

    def test_write_failure_closes_exact_failed_connection(self):
        serial_conn = _FakeSerial(fail_on_write='synthetic\n')
        self.driver.serial_conn = serial_conn

        self.assertFalse(self.driver.write_raw('synthetic\n'))
        self.assertIsNone(self.driver.serial_conn)
        self.assertFalse(serial_conn.is_open)
        self.assertEqual(serial_conn.close_count, 1)

    def test_disappeared_device_is_closed_before_reconnect_attempt(self):
        serial_conn = _FakeSerial()
        self.driver.port = '/dev/osrbot_base'
        self.driver.serial_conn = serial_conn
        with mock.patch.object(DRIVER.os.path, 'exists', return_value=False), mock.patch.object(
            DRIVER.serial, 'Serial'
        ) as serial_factory:
            self.driver.ensure_connected()

        self.assertIsNone(self.driver.serial_conn)
        self.assertFalse(serial_conn.is_open)
        self.driver.start_reader.assert_not_called()
        serial_factory.assert_not_called()

    def test_shutdown_sends_link_down_before_close(self):
        serial_conn = _FakeSerial()
        self.driver.serial_conn = serial_conn
        self.driver.close_serial()

        self.assertEqual(serial_conn.writes, [self.data['startup']['shutdown_host_command']])
        self.assertFalse(serial_conn.is_open)

    def test_expected_shutdown_read_error_is_silent_and_does_not_close_again(self):
        serial_conn = _FakeSerial()
        self.driver.serial_conn = serial_conn
        self.driver.close_serial = mock.Mock()

        def fail_during_shutdown():
            self.driver.shutdown_event.set()
            raise TypeError('synthetic expected shutdown read failure')

        serial_conn.readline = fail_during_shutdown
        self.driver.read_loop()

        self.assertEqual(self.driver.logger.warnings, [])
        self.driver.close_serial.assert_not_called()

    def test_shutdown_waits_for_reader_and_preserves_link_down_cleanup(self):
        serial_conn = _FakeSerial()
        reader = mock.Mock()
        reader.is_alive.return_value = True
        self.driver.serial_conn = serial_conn
        self.driver.reader_thread = reader

        self.driver.shutdown_driver()

        self.assertTrue(self.driver.shutdown_event.is_set())
        self.assertEqual(serial_conn.writes, [self.data['startup']['shutdown_host_command']])
        self.assertFalse(serial_conn.is_open)
        reader.join.assert_called_once_with(timeout=1.0)

    def test_shutdown_prevents_timer_reconnect(self):
        self.driver.shutdown_event.set()

        with mock.patch.object(DRIVER.serial, 'Serial') as serial_factory:
            self.driver.ensure_connected()

        serial_factory.assert_not_called()
        self.driver.start_reader.assert_not_called()

    def test_close_cleanup_swallows_nonstandard_close_error(self):
        serial_conn = _FakeSerial()
        serial_conn.close = mock.Mock(side_effect=RuntimeError('synthetic close failure'))
        self.driver.serial_conn = serial_conn

        self.driver.close_serial()

        self.assertIsNone(self.driver.serial_conn)
        serial_conn.close.assert_called_once_with()

    def test_connected_device_gets_periodic_link_ping(self):
        serial_conn = _FakeSerial()
        self.driver.serial_conn = serial_conn

        self.driver.refresh_connection_status()

        self.assertEqual(serial_conn.writes, [self.data['startup']['periodic_host_command']])

    def test_stale_reader_closes_only_its_captured_connection(self):
        stale_conn = _FakeSerial()
        replacement_conn = _FakeSerial()
        self.driver.serial_conn = stale_conn

        def fail_after_reconnect():
            self.driver.serial_conn = replacement_conn
            raise TypeError('synthetic stale reader failure')

        stale_conn.readline = fail_after_reconnect
        self.driver.read_loop()

        self.assertIs(self.driver.serial_conn, replacement_conn)
        self.assertFalse(stale_conn.is_open)
        self.assertTrue(replacement_conn.is_open)

    def test_reader_finally_preserves_replacement_under_serial_lock(self):
        class CountingLock:
            def __init__(self):
                self.lock = threading.Lock()
                self.enter_count = 0

            def __enter__(self):
                self.lock.acquire()
                self.enter_count += 1
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                self.lock.release()

        serial_conn = _FakeSerial()
        replacement_reader = object()
        counting_lock = CountingLock()
        self.driver.serial_lock = counting_lock
        self.driver.serial_conn = serial_conn
        self.driver.reader_thread = threading.current_thread()

        def fail_after_reader_replacement():
            self.driver.reader_thread = replacement_reader
            raise TypeError('synthetic reader replacement')

        serial_conn.readline = fail_after_reader_replacement
        self.driver.read_loop()

        self.assertIs(self.driver.reader_thread, replacement_reader)
        self.assertEqual(counting_lock.enter_count, 3)

    def test_type_error_on_write_fails_closed(self):
        serial_conn = _FakeSerial()
        serial_conn.write = mock.Mock(side_effect=TypeError('synthetic write type error'))
        self.driver.serial_conn = serial_conn

        self.assertFalse(self.driver.write_raw('synthetic\n'))
        self.assertIsNone(self.driver.serial_conn)
        self.assertFalse(serial_conn.is_open)

    def test_write_failure_cleanup_swallows_nonstandard_close_error(self):
        serial_conn = _FakeSerial(fail_on_write='synthetic\n')
        serial_conn.close = mock.Mock(side_effect=RuntimeError('synthetic close failure'))
        self.driver.serial_conn = serial_conn

        self.assertFalse(self.driver.write_raw('synthetic\n'))

        self.assertIsNone(self.driver.serial_conn)
        serial_conn.close.assert_called_once_with()


class MainLifecycleTests(unittest.TestCase):
    def test_repeated_sigint_is_ignored_during_cleanup(self):
        node = mock.Mock()
        with mock.patch.object(DRIVER, 'ChassisDriver', return_value=node), mock.patch.object(
            DRIVER.rclpy, 'init', create=True
        ), mock.patch.object(
            DRIVER.rclpy, 'spin', side_effect=KeyboardInterrupt(), create=True
        ), mock.patch.object(
            DRIVER.rclpy, 'ok', return_value=False
        ), mock.patch.object(
            DRIVER.rclpy, 'shutdown', create=True
        ), mock.patch.object(signal, 'signal') as set_signal:
            node.shutdown_driver.side_effect = lambda: self.assertEqual(
                set_signal.call_args,
                mock.call(signal.SIGINT, signal.SIG_IGN),
            )

            DRIVER.main()

        node.shutdown_driver.assert_called_once_with()

    def test_external_shutdown_is_clean_and_does_not_shutdown_context_twice(self):
        node = mock.Mock()
        with mock.patch.object(DRIVER, 'ChassisDriver', return_value=node), mock.patch.object(
            DRIVER.rclpy, 'init', create=True
        ), mock.patch.object(
            DRIVER.rclpy, 'spin', side_effect=_ExternalShutdownException(), create=True
        ), mock.patch.object(
            DRIVER.rclpy, 'ok', return_value=False
        ), mock.patch.object(
            DRIVER.rclpy, 'shutdown', create=True
        ) as shutdown:
            DRIVER.main()

        node.shutdown_driver.assert_called_once_with()
        node.destroy_node.assert_called_once_with()
        shutdown.assert_not_called()

    def test_already_shutdown_context_is_not_shutdown_again(self):
        node = mock.Mock()
        with mock.patch.object(DRIVER, 'ChassisDriver', return_value=node), mock.patch.object(
            DRIVER.rclpy, 'init', create=True
        ), mock.patch.object(
            DRIVER.rclpy, 'spin', create=True
        ), mock.patch.object(
            DRIVER.rclpy, 'ok', return_value=False
        ), mock.patch.object(
            DRIVER.rclpy, 'shutdown', create=True
        ) as shutdown:
            DRIVER.main()

        node.shutdown_driver.assert_called_once_with()
        shutdown.assert_not_called()


class ControlMappingTests(unittest.TestCase):
    def setUp(self):
        self.driver = _driver_shell()
        self.driver.max_speed = 0.8
        self.driver.max_steering_angle = math.radians(30.0)
        self.driver.wheelbase = 0.325
        self.driver.clock = _Clock(123)
        self.driver.get_clock = lambda: self.driver.clock
        self.driver.last_cmd_time = _TimePoint(0)
        self.driver.write_raw = mock.Mock(return_value=True)

    def test_ackermann_drive_matches_accepted_serial_mapping(self):
        message = DRIVER.AckermannDrive()
        message.speed = 0.3
        message.steering_angle = 0.1

        self.driver.ackermann_cmd_callback(message)

        self.driver.write_raw.assert_called_once_with('v 0.300 5.73\n')

    def test_base_configuration_bounds_ackermann_command(self):
        message = DRIVER.AckermannDrive()
        message.speed = 1.2
        message.steering_angle = math.radians(40.0)

        self.driver.ackermann_cmd_callback(message)

        self.driver.write_raw.assert_called_once_with('v 0.800 30.00\n')
        self.assertEqual(self.driver.last_cmd_time.nanoseconds, 123)

    def test_twist_maps_to_ackermann_steering(self):
        message = DRIVER.Twist()
        message.linear.x = 0.4
        message.angular.z = 0.2
        expected_degrees = math.degrees(math.atan(0.325 * 0.2 / 0.4))

        self.driver.cmd_vel_callback(message)

        self.driver.write_raw.assert_called_once_with(f'v 0.400 {expected_degrees:.2f}\n')

    def test_cmd_vel_near_zero_boundary_matches_c329(self):
        message = DRIVER.Twist()
        message.linear.x = 0.009
        message.angular.z = 0.0005

        self.driver.cmd_vel_callback(message)

        self.driver.write_raw.assert_called_once_with('v 0.009 30.00\n')

        self.driver.write_raw.reset_mock()
        message.linear.x = 0.01
        expected_degrees = math.degrees(math.atan(0.325 * message.angular.z / message.linear.x))
        self.driver.cmd_vel_callback(message)
        self.driver.write_raw.assert_called_once_with(f'v 0.010 {expected_degrees:.2f}\n')

    def test_failed_command_does_not_refresh_watchdog(self):
        self.driver.write_raw.return_value = False
        previous = self.driver.last_cmd_time
        message = DRIVER.AckermannDrive()
        message.speed = 0.2

        self.driver.ackermann_cmd_callback(message)

        self.assertIs(self.driver.last_cmd_time, previous)


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.driver = _driver_shell()
        self.driver.clock = _Clock()
        self.driver.get_clock = lambda: self.driver.clock
        self.driver.last_cmd_time = _TimePoint(0)
        self.driver.cmd_timeout = 0.5
        self.driver.write_raw = mock.Mock(return_value=True)

    def test_watchdog_stops_only_after_500_ms(self):
        self.driver.clock.nanoseconds = 499_000_000
        self.driver.watchdog_check()
        self.driver.write_raw.assert_not_called()

        self.driver.clock.nanoseconds = 501_000_000
        self.driver.watchdog_check()
        self.driver.write_raw.assert_called_once_with('v 0.00 0.00\n')

    def test_watchdog_boundary_matches_validated_behavior(self):
        self.driver.clock.nanoseconds = 500_000_000
        self.driver.watchdog_check()
        self.driver.write_raw.assert_not_called()


class CiContractTests(unittest.TestCase):
    def test_workflow_is_read_only_and_runs_ros_build_tests(self):
        workflow = WORKFLOW_PATH.read_text(encoding='utf-8')
        self.assertIn('permissions:', workflow)
        self.assertIn('contents: read', workflow)
        self.assertIn('humble', workflow)
        self.assertIn('jazzy', workflow)
        self.assertIn('ubuntu-22.04', workflow)
        self.assertIn('ubuntu-24.04', workflow)
        self.assertRegex(workflow, r'actions/checkout@[0-9a-f]{40}')
        self.assertRegex(workflow, r'ros-tooling/setup-ros@[0-9a-f]{40}')
        self.assertIn('persist-credentials: false', workflow)
        self.assertIn('rosdep install', workflow)
        self.assertIn('PYTHONPYCACHEPREFIX', workflow)
        self.assertIn('python3 -m compileall -q setup.py osracer_base launch test', workflow)
        self.assertNotIn('python3 -m py_compile', workflow)
        self.assertIn("ET.parse('package.xml')", workflow)
        self.assertIn("rglob('*.json')", workflow)
        self.assertIn(
            'uses: astral-sh/ruff-action@278981a28ce3188b1e39527901f38254bf3aac89',
            workflow,
        )
        self.assertRegex(workflow, r"version:\s*['\"]0\.15\.13['\"]")
        self.assertRegex(workflow, r'args:\s*check')
        self.assertRegex(workflow, r'src:\s*\.')
        self.assertIn('colcon build', workflow)
        self.assertIn('colcon test', workflow)
        self.assertIn('colcon test-result --verbose', workflow)
        for forbidden in ('git push', 'pull_request_target', 'create-pull-request', 'release: write'):
            self.assertNotIn(forbidden, workflow)


if __name__ == '__main__':
    unittest.main()
