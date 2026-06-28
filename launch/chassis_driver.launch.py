from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument('port', default_value='/dev/osrbot_base'),
        DeclareLaunchArgument('baudrate', default_value='460800'),
        DeclareLaunchArgument('wheelbase', default_value='0.325'),
        DeclareLaunchArgument('max_speed', default_value='0.8'),
        DeclareLaunchArgument('speed_mode', default_value='high'),
        DeclareLaunchArgument('max_steering_angle', default_value='0.5235987756'),
        DeclareLaunchArgument('cmd_timeout', default_value='0.5'),
        DeclareLaunchArgument('firmware_version_timeout', default_value='0.5'),
        DeclareLaunchArgument('connection_status_enabled', default_value='true'),
        DeclareLaunchArgument('connection_refresh_period', default_value='1.0'),
        DeclareLaunchArgument('odom_frame_id', default_value='odom'),
        DeclareLaunchArgument('base_frame_id', default_value='base_footprint'),
        DeclareLaunchArgument('imu_frame_id', default_value='imu_link'),
        DeclareLaunchArgument('publish_tf', default_value='true'),
    ]

    driver = Node(
        package='osracer_base',
        executable='chassis_driver',
        name='osracer_base',
        output='screen',
        parameters=[{
            'port': LaunchConfiguration('port'),
            'baudrate': LaunchConfiguration('baudrate'),
            'wheelbase': LaunchConfiguration('wheelbase'),
            'max_speed': LaunchConfiguration('max_speed'),
            'speed_mode': LaunchConfiguration('speed_mode'),
            'max_steering_angle': LaunchConfiguration('max_steering_angle'),
            'cmd_timeout': LaunchConfiguration('cmd_timeout'),
            'firmware_version_timeout': LaunchConfiguration('firmware_version_timeout'),
            'connection_status_enabled': LaunchConfiguration('connection_status_enabled'),
            'connection_refresh_period': LaunchConfiguration('connection_refresh_period'),
            'odom_frame_id': LaunchConfiguration('odom_frame_id'),
            'base_frame_id': LaunchConfiguration('base_frame_id'),
            'imu_frame_id': LaunchConfiguration('imu_frame_id'),
            'publish_tf': LaunchConfiguration('publish_tf'),
        }],
    )

    return LaunchDescription(args + [driver])
