import os
from glob import glob

from setuptools import find_packages, setup

package_name = "ros2_py_pkg"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test", "test.*"]),
    # install() 卫生（《产品打包构建说明》）：装 resource marker + package.xml + launch，
    # 让 colcon build --install 能把包打进二进制版本。
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="your name",
    maintainer_email="you@example.com",
    description="ROS 2 ament_python 参考包（请重命名为你的包名）。",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "talker = ros2_py_pkg.talker_node:main",
        ],
    },
)
