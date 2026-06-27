cmake_minimum_required(VERSION 3.0.2)
project(osracer_base)

find_package(catkin REQUIRED COMPONENTS
  ackermann_msgs
  geometry_msgs
  nav_msgs
  rospy
  sensor_msgs
  tf2_ros
)

catkin_python_setup()

catkin_package()

catkin_install_python(PROGRAMS
  scripts/chassis_driver.py
  scripts/check_device.py
  scripts/install_udev_rules.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch rviz scripts udev
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
  USE_SOURCE_PERMISSIONS
)

install(FILES README.md README_zh.md
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
