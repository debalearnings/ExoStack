from launch import LaunchDescription
from launch_ros.actions import Node
import os
import yaml

def generate_launch_description():
    home = os.path.expanduser("~")
    profile_yaml = os.path.join(home, "exo_stack_resources", "config", "profile.yaml")

    with open(profile_yaml, "r") as f:
        profiles_cfg = yaml.safe_load(f)["profiles"]

    nodes = []
    for profile_name, cfg in profiles_cfg.items():
        if cfg.get("mode") == "HIL":
            nodes.append(
                Node(
                    package="exo_stack",
                    executable="hil",  # your Generic HIL node
                    name=f"{profile_name}_hil",
                    output="screen",
                    arguments=[profile_name]  # <-- passed as sys.argv[1]
                )
            )

    return LaunchDescription(nodes)
