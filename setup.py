from catkin_pkg.python_setup import generate_distutils_setup
from distutils.core import setup

setup_args = generate_distutils_setup(
    packages=['osracer_base', 'osracer_base.tools'],
    package_dir={'': '.'},
)

setup(**setup_args)
