# launch/gait_event_detector_launch.py

import os
import yaml

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # Path to the gait_events.yaml
    config_path = os.path.expanduser('~/exo_stack_resources/config/gait_events.yaml')

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Only get the events dictionary
    events_cfg = config.get("events", {})
    if not events_cfg:
        raise RuntimeError("No events defined under 'events:' in gait_events.yaml")

    launch_nodes = []

    for event_key in events_cfg.keys():
        node = Node(
            package='exo_stack',             # Replace with your package name
            executable='gait_event_detector',     # Your node script
            name=f"{event_key}_event",                          # Node name = event_key
            output='screen',
            arguments=[event_key]                     # Pass event_key as command-line arg
        )
        launch_nodes.append(node)

    return LaunchDescription(launch_nodes)
