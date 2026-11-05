# launch/mplanner_launch.py

import os
import yaml

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # Path to the mplanner.yaml
    config_path = os.path.expanduser('~/exo_stack_resources/config/mplanner.yaml')

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Only get the planners dictionary
    planners_cfg = config.get("planners", {})
    if not planners_cfg:
        raise RuntimeError("No planners defined under 'planners:' in mplanner.yaml")

    launch_nodes = []

    for planner_key in planners_cfg.keys():
        node = Node(
            package='exo_stack',                # Replace with your package name
            executable='mplanner',        # Your generic planner node script
            name=f"{planner_key}_planner",                  # Node name = planner_key
            output='screen',
            arguments=[planner_key]            # Pass planner_key as command-line argument
        )
        launch_nodes.append(node)

    return LaunchDescription(launch_nodes)
