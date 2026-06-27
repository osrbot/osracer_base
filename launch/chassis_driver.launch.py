from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument('port', default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('baudrate', default_value='460800'),
        DeclareLaunchArgument('wheelbase', default_value='0.285'),
        DeclareLaunchArgument('max_speed', default_value='3.0'),
        DeclareLaunchArgument('max_steering_angle', default_value='0.5235987756'),
        DeclareLaunchArgument('cmd_timeout', default_value='0.5'),
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
            'max_steering_angle': LaunchConfiguration('max_steering_angle'),
            'cmd_timeout': LaunchConfiguration('cmd_timeout'),
            'odom_frame_id': LaunchConfiguration('odom_frame_id'),
            'base_frame_id': LaunchConfiguration('base_frame_id'),
            'imu_frame_id': LaunchConfiguration('imu_frame_id'),
            'publish_tf': LaunchConfiguration('publish_tf'),
        }],
    )

    return LaunchDescription(args + [driver])
