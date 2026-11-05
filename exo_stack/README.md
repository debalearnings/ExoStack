# ExoCore (`exo_stack`): generic ROS 2 nodes

ROS 2 Python package (`ament_python`) with the host-side nodes of ExoStack. Each node is created from one entry of a YAML file in `~/exo_stack_resources/config`, and loads its algorithms by name from `~/exo_stack_resources/algo` and `planner`.

| Executable | Role | Launch file |
|---|---|---|
| `sync` | time-synchronizes the hub topics into `/synced_sensors` | no launch file: `ros2 run exo_stack sync` |
| `gait_event_detector` | gait-event detection | `gait_event_detector_launch.py` |
| `mplanner` | motion planner | `mplanner_launch.py` |
| `actuation_profile` | profile node (lookup table or HIL candidate → profile) | `profile_launch.py` |
| `cost` | per-gait-cycle cost for HIL | `cost_launch.py` |
| `hil` | HIL optimizer | `hil_launch.py` |

## Requirements

- Ubuntu 22.04, ROS 2 Humble (desktop), Python 3.10
- Python packages: [`requirements.txt`](requirements.txt): `numpy`, `scipy`, `pyyaml`, `cmaes`, `bayesian-optimization==1.4.3`
- The workspace folder [`exo_stack_resources`](../exo_stack_resources) in your home directory

## Install

If the repository is cloned into `~/ros2_ws/src` (colcon finds the package inside it):

```bash
cd ~/ros2_ws/src/ExoStack
pip3 install -r exo_stack/requirements.txt
cd ~/ros2_ws
colcon build --packages-select exo_stack
source install/setup.bash
```

Check:

```bash
ros2 pkg executables exo_stack          # lists sync, gait_event_detector, mplanner, actuation_profile, cost, hil, ...
ros2 launch exo_stack gait_event_detector_launch.py --show-args
```

Back to the [main README](../README.md).
