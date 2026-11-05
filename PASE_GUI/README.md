# PASE: configure, launch, visualize

PyQt5 desktop application for ExoStack. It runs in place; nothing is installed.

| Tab | Function |
|---|---|
| **Configuration** | four linked editors for `sensors.yaml`, `gait_events.yaml`, `mplanner.yaml`, `profile.yaml` in `~/exo_stack_resources/config` |
| **Launch** | starts and stops the micro-ROS agents and the six ExoCore stages, and shows which configured nodes are alive |
| **Visualization** | live plots of any topic field, with event markers, split views and saved layouts |

## Requirements

- ROS 2 Humble sourced in the terminal (PASE uses `rclpy` and starts the ExoCore stages)
- Python packages: [`requirements.txt`](requirements.txt): `PyQt5`, `pyqtgraph`, `ruamel.yaml`, `cmaes`, `bayesian-optimization`
- ExoCore built, and `~/exo_stack_resources` in place (see the [main README](../README.md))

## Run

```bash
cd PASE_GUI                      # PASE loads its icons relative to this folder
pip3 install -r requirements.txt
python3 main.py
```

Back to the [main README](../README.md).
