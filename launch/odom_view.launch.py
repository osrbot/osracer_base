from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare('osracer_base')

    args = [
        DeclareLaunchArgument('port', default_value='/dev/osrbot_base'),
        DeclareLaunchArgument('baudrate', default_value='460800'),
        DeclareLaunchArgument('wheelbase', default_value='0.325'),
        DeclareLaunchArgument('max_speed', default_value='0.8'),
        DeclareLaunchArgument('speed_mode', default_value='high'),
        DeclareLaunchArgument('max_steering_angle', default_value='0.5235987756'),
        DeclareLaunchArgument('cmd_timeout', default_value='0.5'),
        DeclareLaunchArgument('odom_frame_id', default_value='odom'),
        DeclareLaunchArgument('base_frame_id', default_value='base_footprint'),
        DeclareLaunchArgument('imu_frame_id', default_value='imu_link'),
        DeclareLaunchArgument('publish_tf', default_value='true'),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=PathJoinSubstitution([package_share, 'rviz', 'odom_view.rviz']),
        ),
    ]

    driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([package_share, 'launch', 'chassis_driver.launch.py'])
        ),
        launch_arguments={
            'port': LaunchConfiguration('port'),
            'baudrate': LaunchConfiguration('baudrate'),
            'wheelbase': LaunchConfiguration('wheelbase'),
            'max_speed': LaunchConfiguration('max_speed'),
            'speed_mode': LaunchConfiguration('speed_mode'),
            'max_steering_angle': LaunchConfiguration('max_steering_angle'),
            'cmd_timeout': LaunchConfiguration('cmd_timeout'),
            'odom_frame_id': LaunchConfiguration('odom_frame_id'),
            'base_frame_id': LaunchConfiguration('base_frame_id'),
            'imu_frame_id': LaunchConfiguration('imu_frame_id'),
            'publish_tf': LaunchConfiguration('publish_tf'),
        }.items(),
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rviz_config')],
    )

    return LaunchDescription(args + [driver, rviz])
