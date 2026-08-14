from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    args = [
        DeclareLaunchArgument('port', default_value='/dev/osrbot_base'),
        DeclareLaunchArgument('baudrate', default_value='460800'),
        DeclareLaunchArgument('cmd_timeout', default_value='0.5'),
        DeclareLaunchArgument('reconnect_interval', default_value='2.0'),
        DeclareLaunchArgument('firmware_version_timeout', default_value='0.3'),
        DeclareLaunchArgument('connection_status_enabled', default_value='true'),
        DeclareLaunchArgument('connection_refresh_period', default_value='1.0'),
        DeclareLaunchArgument('odom_frame_id', default_value='odom'),
        DeclareLaunchArgument('base_frame_id', default_value='base_footprint'),
        DeclareLaunchArgument('imu_frame_id', default_value='imu_link'),
        DeclareLaunchArgument('publish_tf', default_value='true'),
        DeclareLaunchArgument('publish_rc', default_value='true'),
        DeclareLaunchArgument('rc_topic', default_value='rc_data'),
        DeclareLaunchArgument('publish_mag', default_value='true'),
        DeclareLaunchArgument('mag_topic', default_value='magnetometer_data'),
        DeclareLaunchArgument('mag_frame_id', default_value='imu_link'),
        DeclareLaunchArgument('imu_orientation_covariance', default_value='[0.02, 0.02, 0.05]'),
        DeclareLaunchArgument('imu_angular_velocity_covariance', default_value='[0.01, 0.01, 0.01]'),
        DeclareLaunchArgument('imu_linear_acceleration_covariance', default_value='[0.10, 0.10, 0.10]'),
        DeclareLaunchArgument('odom_twist_covariance', default_value='[0.02, 0.20, 1.0, 1.0, 1.0, 0.30]'),
        DeclareLaunchArgument('publish_battery', default_value='true'),
        DeclareLaunchArgument('battery_topic', default_value='battery_state'),
    ]

    driver = Node(
        package='osracer_base',
        executable='chassis_driver',
        name='osracer_base',
        output='screen',
        parameters=[{
            'port': LaunchConfiguration('port'),
            'baudrate': LaunchConfiguration('baudrate'),
            'cmd_timeout': LaunchConfiguration('cmd_timeout'),
            'reconnect_interval': LaunchConfiguration('reconnect_interval'),
            'firmware_version_timeout': LaunchConfiguration('firmware_version_timeout'),
            'connection_status_enabled': LaunchConfiguration('connection_status_enabled'),
            'connection_refresh_period': LaunchConfiguration('connection_refresh_period'),
            'odom_frame_id': LaunchConfiguration('odom_frame_id'),
            'base_frame_id': LaunchConfiguration('base_frame_id'),
            'imu_frame_id': LaunchConfiguration('imu_frame_id'),
            'publish_tf': LaunchConfiguration('publish_tf'),
            'publish_rc': LaunchConfiguration('publish_rc'),
            'rc_topic': LaunchConfiguration('rc_topic'),
            'publish_mag': LaunchConfiguration('publish_mag'),
            'mag_topic': LaunchConfiguration('mag_topic'),
            'mag_frame_id': LaunchConfiguration('mag_frame_id'),
            'imu_orientation_covariance': ParameterValue(
                LaunchConfiguration('imu_orientation_covariance'), value_type=list[float]
            ),
            'imu_angular_velocity_covariance': ParameterValue(
                LaunchConfiguration('imu_angular_velocity_covariance'), value_type=list[float]
            ),
            'imu_linear_acceleration_covariance': ParameterValue(
                LaunchConfiguration('imu_linear_acceleration_covariance'), value_type=list[float]
            ),
            'odom_twist_covariance': ParameterValue(
                LaunchConfiguration('odom_twist_covariance'), value_type=list[float]
            ),
            'publish_battery': LaunchConfiguration('publish_battery'),
            'battery_topic': LaunchConfiguration('battery_topic'),
        }],
    )

    return LaunchDescription(args + [driver])
