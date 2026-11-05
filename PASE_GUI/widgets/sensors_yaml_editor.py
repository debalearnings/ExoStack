import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QGroupBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml import YAML
import os

def normalize_topic(s):
    """Return a topic with exactly one leading slash (empty stays empty)."""
    s = (s or "").strip()
    return ("/" + s.lstrip("/")) if s else ""


class SensorsYamlEditor(QWidget):
    def __init__(self, parent=None, width=400, title="Sensors", signal_bus=None ):
        super().__init__(parent)
        self.signal_bus = signal_bus

        self.hub_widgets = []
        self.setFixedWidth(width)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # --- Section heading ---
        section_label = QLabel(title)
        section_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(section_label)

        # --- Slop time input ---
        slop_layout = QHBoxLayout()
        slop_label = QLabel("Slop time:")
        self.slop_input = QLineEdit("0.15")
        slop_layout.addWidget(slop_label)
        slop_layout.addWidget(self.slop_input)
        slop_layout.addStretch()
        main_layout.addLayout(slop_layout)

        # --- Output topic input ---
        output_layout = QHBoxLayout()
        output_label = QLabel("Output topic:")
        self.output_input = QLineEdit("/synced_sensors")
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addStretch()
        main_layout.addLayout(output_layout)

       # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_content = QWidget()
        self.hub_column = QVBoxLayout(scroll_content)
        self.hub_column.setSpacing(5)  # hubs close together vertically
        self.hub_column.setContentsMargins(0, 0, 0, 0)
        self.hub_column.setAlignment(Qt.AlignTop)  # keep all events at top


        self.scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.scroll_area)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add Hub")
        add_btn.clicked.connect(self.add_hub)
        save_btn = QPushButton("Save YAML")
        save_btn.clicked.connect(self.save_yaml)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # # Add initial hub
        # self.add_hub()

        self.yaml_path = os.path.join(os.path.expanduser("~"), "exo_stack_resources", "config", "sensors.yaml")

        # --- Auto-load YAML content (if exists) ---


        self.load_yaml()


    def add_hub(self, hub_name="", topic="", sensors=""):
        hub_box = QGroupBox("Hub")
        hub_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout()  # vertical layout for fields
        layout.setSpacing(5)

        # Hub Name
        hub_name_edit = QLineEdit()
        hub_name_edit.setPlaceholderText("Hub name")
        layout.addWidget(QLabel("Hub Name:"))
        hub_name_edit.setText(hub_name if hub_name else "")
        layout.addWidget(hub_name_edit)

        # Topic Name
        topic_edit = QLineEdit()
        topic_edit.setPlaceholderText("/topic_name")
        layout.addWidget(QLabel("Topic Name:"))
        topic_edit.setText(topic if topic else "")
        layout.addWidget(topic_edit)

        # Sensors
        sensors_edit = QLineEdit()
        sensors_edit.setPlaceholderText("Sensors (comma-separated)")
        layout.addWidget(QLabel("Sensors:"))
        sensors_edit.setText(sensors if sensors else "")
        layout.addWidget(sensors_edit)

        # Remove button at the bottom
        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("role", "danger")
        layout.addWidget(remove_btn)

        hub_box.setLayout(layout)
        self.hub_column.addWidget(hub_box)

        self.hub_widgets.append({
            "container": hub_box,
            "hub_name": hub_name_edit,
            "topic": topic_edit,
            "sensors": sensors_edit
        })

        remove_btn.clicked.connect(lambda: self.remove_hub(hub_box))

    def remove_hub(self, hub_box):
        for i, w in enumerate(self.hub_widgets):
            if w["container"] == hub_box:
                self.hub_column.removeWidget(hub_box)
                hub_box.setParent(None)
                self.hub_widgets.pop(i)
                break

    def save_yaml(self):
        yaml_data = {"hubs": {}}
        for w in self.hub_widgets:
            hub_name = w["hub_name"].text().strip()
            topic_name = w["topic"].text().strip()
            sensors = [s.strip() for s in w["sensors"].text().split(",") if s.strip()]
            if hub_name and topic_name:
                sensors_seq = CommentedSeq(sensors)
                sensors_seq.fa.set_flow_style()
                yaml_data["hubs"][hub_name] = {
                    "topic": normalize_topic(topic_name),
                    "sensors": sensors_seq
                }

        try:
            slop_time_value = float(self.slop_input.text().strip())
        except ValueError:
            slop_time_value = 0.15

        output_topic_value = normalize_topic(self.output_input.text())

        yaml_data["slop_time"] = slop_time_value
        yaml_data["output_topic"] = output_topic_value

        
        os.makedirs(os.path.dirname(self.yaml_path), exist_ok=True)

        yaml = YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(self.yaml_path, "w") as f:
            yaml.dump(yaml_data, f)

        print(f"YAML saved at {self.yaml_path}")

        if self.signal_bus:
            self.signal_bus.sensors_updated.emit()



    def load_yaml(self):
        """Load YAML file (if it exists) and populate UI fields"""
        if not os.path.exists(self.yaml_path):
            print(f"[WARN] sensors.yaml not found at {self.yaml_path}")
            self.slop_input.setText("0.15")
            self.output_input.setText("/synced_sensors")
            self.add_hub()  # blank hub
            return

        yaml = YAML()
        try:
            with open(self.yaml_path, "r") as f:
                data = yaml.load(f) or {}  # <<< important: empty file gives {}
        except Exception as e:
            print(f"[ERROR] Failed to load sensors.yaml: {e}")
            self.slop_input.setText("0.15")
            self.output_input.setText("/synced_sensors")
            self.add_hub()  # blank hub
            return

        # Clear previous hubs
        for w in self.hub_widgets[:]:
            self.remove_hub(w["container"])

        # Populate slop time and output topic safely
        self.slop_input.setText(str(data.get("slop_time", 0.15)))
        self.output_input.setText(str(data.get("output_topic", "/synced_sensors")))

        # Add hubs
        hubs = data.get("hubs", {})
        if hubs:
            for hub_name, hub_info in hubs.items():
                topic = normalize_topic(hub_info.get("topic", ""))
                sensors = ", ".join(hub_info.get("sensors", []))
                self.add_hub(hub_name=hub_name, topic=topic, sensors=sensors)
        else:
            # If no hubs found, show one empty hub
            self.add_hub()

        print(f"[INFO] sensors.yaml loaded successfully from {self.yaml_path}")

