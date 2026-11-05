# exo_stack_resources: configuration, plug-ins, data

The user workspace read by ExoCore and PASE. It must be located at **`~/exo_stack_resources`**, directly in your home directory.

| Folder | Content |
|---|---|
| [`config/`](config) | `sensors.yaml`, `gait_events.yaml`, `mplanner.yaml`, `profile.yaml` |
| [`algo/`](algo) | plug-ins: `gait_events/`, `builder/`, `lookup_algo/`, `hil_optimizer/`, `cost/` |
| [`planner/`](planner) | motion-planner plug-ins |
| [`lookup_table/`](lookup_table) | JSON lookup tables (speed, intent → profile parameters) |
| [`util/`](util) | `SensorUtil.py`: maps channel names to message indices |
| [`hil_results/`](hil_results) | CSV files written by the HIL optimizer |

## Install

From the root of the cloned repository:

```bash
cp -r exo_stack_resources ~/            # creates ~/exo_stack_resources
```

If `~/exo_stack_resources` already holds your own configuration, copy into it instead of replacing it:
`cp -rn exo_stack_resources/. ~/exo_stack_resources/` (existing files are kept).

The shipped `config/` is a complete bilateral example to start from; PASE edits these files, or edit them by hand.

Back to the [main README](../README.md).
