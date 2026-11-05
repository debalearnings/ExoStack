import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from widgets.sensors_yaml_editor import SensorsYamlEditor
from widgets.gait_events_yaml_editor import GaitEventsYamlEditor
from widgets.motion_planner_yaml_editor import MotionPlannerYamlEditor
from widgets.profile_yaml_editor import ProfileYamlEditor
import os

os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"


class ConfigTab(QWidget):
    def __init__(self, signal_bus):
        super().__init__()

        self.signal_bus = signal_bus

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)  # Space between the three panels

        # --- Left side: Sensors YAML editor ---
        sensors_editor = SensorsYamlEditor(width=250, signal_bus=self.signal_bus)
        sensors_editor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # --- Middle: Gait Events YAML editor ---
        sensors_yaml_path = os.path.join(os.path.expanduser("~"),
                                         "exo_stack_resources", "config", "sensors.yaml")
        gait_events_editor = GaitEventsYamlEditor(
            sensors_yaml_path=sensors_yaml_path,
            width=300,
            signal_bus=self.signal_bus
        )
        gait_events_editor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # --- Right side: Motion Planners YAML editor ---
        motion_planner_editor = MotionPlannerYamlEditor(
            gait_events_yaml_path=os.path.join(
                os.path.expanduser("~"),
                "exo_stack_resources",
                "config",
                "gait_events.yaml"
            ),
            width=300,
            signal_bus=self.signal_bus
        )
        motion_planner_editor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)




        # --- Right side (or another column) ---
        profile_editor = ProfileYamlEditor(
            mplanner_yaml_path=os.path.join(
            os.path.expanduser("~"),
            "exo_stack_resources",
            "config",
            "mplanner.yaml"
            ),
            sensors_yaml_path=os.path.join(
            os.path.expanduser("~"),
            "exo_stack_resources",
            "config",
            "sensors.yaml"
            ),
            width=480,
            signal_bus=self.signal_bus
            )
        profile_editor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)




        # Add editors to horizontal layout
        main_layout.addWidget(sensors_editor)
        main_layout.addWidget(gait_events_editor)
        main_layout.addWidget(motion_planner_editor)
        main_layout.addWidget(profile_editor)

        # Store references
        self.sensors_editor = sensors_editor
        self.gait_events_editor = gait_events_editor
        self.motion_planner_editor = motion_planner_editor
        self.profile_editor = profile_editor

        self.setLayout(main_layout)
