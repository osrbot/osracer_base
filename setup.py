from glob import glob
from setuptools import find_packages, setup

package_name = 'osracer_base'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml', 'README.md', 'README_zh.md']),
        (f'share/{package_name}/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='osrbot',
    maintainer_email='osrbot@osrbot.com',
    description='Minimal ROS 2 chassis driver for OSRacer.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'chassis_driver = osracer_base.chassis_driver:main',
        ],
    },
)
