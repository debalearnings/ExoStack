import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QGroupBox, QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml import YAML
import os

def normalize_topic(s):
    s=(s or "").strip()
    return ("/"+s.lstrip("/")) if s else ""


class MotionPlannerYamlEditor(QWidget):
    def __init__(self, gait_events_yaml_path=None, width=300, title="Motion Planners", signal_bus=None):
        super().__init__()
        self.signal_bus = signal_bus
        self.gait_events_yaml_path=gait_events_yaml_path
        self.setFixedWidth(width)
        self.planner_widgets = []

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5,5,5,5)
        main_layout.setSpacing(5)

        # --- Section heading ---
        heading = QLabel(title)
        heading.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(heading)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_content = QWidget()
        self.planner_column = QVBoxLayout(scroll_content)
        self.planner_column.setSpacing(5)  # planners close together vertically
        self.planner_column.setContentsMargins(0,0,0,0)
        self.planner_column.setAlignment(Qt.AlignTop)  # keep all planners at top
    
        self.scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.scroll_area)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add Planner")
        add_btn.clicked.connect(self.add_planner)
        save_btn = QPushButton("Save YAML")
        save_btn.clicked.connect(self.save_yaml)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # --- Load gait events for dropdown ---
        self.load_gait_events()

        if self.signal_bus:
         self.signal_bus.gait_events_updated.connect(self.reload_gait_events_yaml)

        # # --- Add initial planner ---
        # self.add_planner()

        # --- Load planners from YAML or add a blank one ---
        self.load_yaml()

    def load_gait_events(self):
        """Load gait events YAML from file and update self.gait_events_topics"""
        self.gait_events_topics = []

        if os.path.exists(self.gait_events_yaml_path):
            from ruamel.yaml import YAML
            yaml = YAML()
            with open(self.gait_events_yaml_path, "r") as f:
                data = yaml.load(f)
            if data and "events" in data:
                for evt_val in data["events"].values():
                    topic = evt_val.get("output_topic", "")
                    if topic:
                        self.gait_events_topics.append(topic)

    def reload_gait_events_yaml(self):
        """Reload gait events data from gait_events.yaml"""
        self.load_gait_events()  # updates self.gait_events_topics

        # Update planner algorithm dropdowns for each planner widget
        for w in self.planner_widgets:
            # Update gait event topic combo
            gait_combo = w["gait_topic"]
            current_topic = gait_combo.currentText()
            gait_combo.blockSignals(True)
            gait_combo.clear()
            gait_combo.addItems(self.gait_events_topics)
            if current_topic in self.gait_events_topics:
                gait_combo.setCurrentText(current_topic)
            gait_combo.blockSignals(False)


    def add_planner(self, planner_name="", gait_event_topic="", planner_algorithm="",
                    profile_topic="", profile_type="List", output_topic="", approach="time_based",
                    rate="", default_output=""):

        planner_box = QGroupBox("Planner")
        planner_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout()
        layout.setSpacing(3)

        # Name
        name_edit = QLineEdit(str(planner_name) if planner_name else "")
        name_edit.setPlaceholderText("Planner name")
        layout.addWidget(QLabel("Planner Name:"))
        layout.addWidget(name_edit)

        # Gait event topic
        gait_combo = QComboBox()
        gait_combo.addItems(self.gait_events_topics)
        if gait_event_topic in self.gait_events_topics:
            gait_combo.setCurrentText(gait_event_topic)
        layout.addWidget(QLabel("Gait Event Topic:"))
        layout.addWidget(gait_combo)

        # Planner algorithm
        algo_combo = QComboBox()
        algo_folder = os.path.join(os.path.expanduser("~"), "exo_stack_resources", "planner")
        algo_files = [f.replace(".py","") for f in os.listdir(algo_folder) if f.endswith(".py")]
        algo_combo.addItems(algo_files)
        if planner_algorithm in algo_files:
            algo_combo.setCurrentText(planner_algorithm)
        layout.addWidget(QLabel("Planner Algorithm:"))
        layout.addWidget(algo_combo)

        # Profile topic
        profile_edit = QLineEdit(str(profile_topic) if profile_topic else "")
        profile_edit.setPlaceholderText("/profile_topic")
        layout.addWidget(QLabel("Profile Topic:"))
        layout.addWidget(profile_edit)

        # Profile type
        profile_type_combo = QComboBox()
        profile_type_combo.addItems(["List", "Function"])
        if profile_type in ["List","Function"]:
            profile_type_combo.setCurrentText(profile_type)
        layout.addWidget(QLabel("Profile Type:"))
        layout.addWidget(profile_type_combo)

        # Output topic
        output_edit = QLineEdit(str(output_topic) if output_topic else "")
        output_edit.setPlaceholderText("/output_topic")
        layout.addWidget(QLabel("Output Topic:"))
        layout.addWidget(output_edit)

        # Approach
        approach_combo = QComboBox()
        approach_combo.addItems(["time_based", "gait_phase"])
        if approach in ["time_based", "gait_phase"]:
            approach_combo.setCurrentText(approach)
        layout.addWidget(QLabel("Approach:"))
        layout.addWidget(approach_combo)

        # Rate
        rate_edit = QLineEdit(str(rate) if rate else "")
        rate_edit.setPlaceholderText("Rate")
        layout.addWidget(QLabel("Rate:"))
        layout.addWidget(rate_edit)

        # Default output
        default_edit = QLineEdit(str(default_output) if default_output else "")
        default_edit.setPlaceholderText("Default Output")
        layout.addWidget(QLabel("Default Output:"))
        layout.addWidget(default_edit)

        # Remove button
        remove_btn = QPushButton("Remove Planner")
        remove_btn.setProperty("role", "danger")
        layout.addWidget(remove_btn)

        if self.signal_bus:
            self.signal_bus.gait_events_updated.connect(self.reload_gait_events_yaml)


        planner_box.setLayout(layout)
        self.planner_column.addWidget(planner_box)

        self.planner_widgets.append({
            "container": planner_box,
            "name": name_edit,
            "gait_topic": gait_combo,
            "algorithm": algo_combo,
            "profile_topic": profile_edit,
            "profile_type": profile_type_combo,
            "output_topic": output_edit,
            "approach": approach_combo,
            "rate": rate_edit,
            "default_output": default_edit
        })

        remove_btn.clicked.connect(lambda: self.remove_planner(planner_box))





    def remove_planner(self, planner_box):
        for i, w in enumerate(self.planner_widgets):
            if w["container"] == planner_box:
                self.planner_column.removeWidget(planner_box)
                planner_box.setParent(None)
                self.planner_widgets.pop(i)
                break

    def save_yaml(self):
        yaml_data = {"planners": {}}
        for w in self.planner_widgets:
            name = w["name"].text().strip()
            if not name:
                continue

            profile_topic = normalize_topic(w["profile_topic"].text())
            output_topic = normalize_topic(w["output_topic"].text())

            yaml_data["planners"][name] = {
                "gait_event_topic": w["gait_topic"].currentText(),
                "planner_algorithm": w["algorithm"].currentText(),
                "profile_topic": profile_topic,
                "profile_type": w["profile_type"].currentText(),
                "output_topic": output_topic,
                "approach": w["approach"].currentText(),
                "rate": int(w["rate"].text().strip()) if w["rate"].text().strip().isdigit() else 0,
                "default_output": float(w["default_output"].text().strip()) if w["default_output"].text().strip() else 0.0
            }

        yaml_path = os.path.join(os.path.expanduser("~"), "exo_stack_resources", "config", "mplanner.yaml")
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)

        yaml = YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(yaml_path, "w") as f:
            yaml.dump(yaml_data, f)

        print(f"Motion Planners YAML saved at {yaml_path}")

        if self.signal_bus:
            self.signal_bus.planners_updated.emit()


    def load_yaml(self):
        """Load motion planners YAML and populate UI fields"""
        yaml_path = os.path.expanduser("~/exo_stack_resources/config/mplanner.yaml")
        if not os.path.exists(yaml_path):
            print(f"[WARN] mplanner.yaml not found at {yaml_path}")
            self.add_planner()  # blank planner
            return

        yaml = YAML()
        try:
            with open(yaml_path, "r") as f:
                data = yaml.load(f) or {}  # ensures empty file gives {}
        except Exception as e:
            print(f"[ERROR] Failed to load mplanner.yaml: {e}")
            self.add_planner()  # blank planner
            return

        # Clear previous planners
        for w in self.planner_widgets[:]:
            self.remove_planner(w["container"])

        planners = data.get("planners", {})
        if not planners:
            # blank planner if none found
            self.add_planner()
            return

        for name, info in planners.items():
            self.add_planner(
                planner_name=name,
                gait_event_topic=info.get("gait_event_topic", ""),
                planner_algorithm=info.get("planner_algorithm", ""),
                profile_topic=info.get("profile_topic", ""),
                profile_type=info.get("profile_type", "List"),
                output_topic=info.get("output_topic", ""),
                approach=info.get("approach", "time_based"),
                rate=info.get("rate", ""),
                default_output=info.get("default_output", "")
            )

        print(f"[INFO] Motion planners YAML loaded from {yaml_path}")

