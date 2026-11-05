import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QComboBox, QSizePolicy, QGroupBox
)
from PyQt5.QtCore import Qt
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml import YAML

def normalize_topic(s):
    s=(s or "").strip()
    return ("/"+s.lstrip("/")) if s else ""


class GaitEventsYamlEditor(QWidget):
    def __init__(self, sensors_yaml_path, width=300, title="Gait Events", signal_bus=None):
        super().__init__()
        self.signal_bus = signal_bus
        self.sensors_yaml_path = sensors_yaml_path
        self.setFixedWidth(width)
        self.event_widgets = []

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5,5,5,5)
        main_layout.setSpacing(5)

        # Section heading
        label = QLabel(title)
        label.setStyleSheet("font-weight:bold; font-size:14px;")
        main_layout.addWidget(label)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_content = QWidget()
        self.events_layout = QVBoxLayout(scroll_content)
        self.events_layout.setSpacing(5)
        self.events_layout.setContentsMargins(0,0,0,0)
        self.events_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add Event")
        add_btn.clicked.connect(self.add_event)
        save_btn = QPushButton("Save YAML")
        save_btn.clicked.connect(self.save_yaml)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # Load hubs and sensors
        self.load_sensors()

        # Connect signal from Sensors editor
        if self.signal_bus:
            self.signal_bus.sensors_updated.connect(self.reload_sensors_yaml)

        # Load available algorithms
        self.algorithms = self.load_algorithms()

        # Load events from YAML
        self.load_yaml()

    def reload_sensors_yaml(self):
        """Reload sensor hubs from sensors.yaml"""
        self.load_sensors()

        for w in self.event_widgets:
            for hub_combo, sensor_combo in w["sensors"]:
                current_hub = hub_combo.currentText()
                hub_combo.blockSignals(True)
                hub_combo.clear()
                hub_combo.addItems(self.hubs.keys())
                if current_hub in self.hubs:
                    hub_combo.setCurrentText(current_hub)
                hub_combo.blockSignals(False)

                current_sensor = sensor_combo.currentText()
                hub = hub_combo.currentText()
                sensor_combo.blockSignals(True)
                sensor_combo.clear()
                sensor_combo.addItems(self.hubs.get(hub, {}).get("sensors", []))
                if current_sensor in self.hubs.get(hub, {}).get("sensors", []):
                    sensor_combo.setCurrentText(current_sensor)
                sensor_combo.blockSignals(False)

    def load_sensors(self):
        self.hubs = {}
        if os.path.exists(self.sensors_yaml_path):
            yaml = YAML()
            with open(self.sensors_yaml_path, 'r') as f:
                data = yaml.load(f) or {}
            self.hubs = data.get('hubs', {})

    def load_algorithms(self):
        algo_dir = os.path.expanduser("~/exo_stack_resources/algo/gait_events")
        if not os.path.exists(algo_dir):
            return []
        files = os.listdir(algo_dir)
        return [f.replace(".py","") for f in files if f.endswith(".py")]

    def add_event(self):
        event_box = QGroupBox("Event")
        event_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        event_box.setMaximumHeight(500)
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Event name
        event_name_edit = QLineEdit()
        event_name_edit.setPlaceholderText("Event name")
        layout.addWidget(QLabel("Event Name:"))
        layout.addWidget(event_name_edit)

        # Input topic
        input_topic_edit = QLineEdit("/synced_sensors")
        input_topic_edit.setPlaceholderText("/input_topic")
        layout.addWidget(QLabel("Input Topic Name:"))
        layout.addWidget(input_topic_edit)

        # Sensor selections
        sensors_layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Sensors:"))
        add_sensor_btn = QPushButton("+ Add Sensor")
        sensors_rows = []

        def add_sensor_row(hub_val=None, sensor_val=None):
            row_layout = QHBoxLayout()
            hub_combo = QComboBox()
            hub_combo.addItems(self.hubs.keys())
            sensor_combo = QComboBox()

            def update_sensors(index):
                hub = hub_combo.currentText()
                sensor_combo.clear()
                sensor_combo.addItems(self.hubs.get(hub, {}).get("sensors", []))

            hub_combo.currentIndexChanged.connect(update_sensors)
            update_sensors(0)

            if hub_val:
                hub_combo.setCurrentText(hub_val)
            if sensor_val:
                sensor_combo.setCurrentText(sensor_val)

            row_layout.addWidget(hub_combo)
            row_layout.addWidget(sensor_combo)
            sensors_layout.addLayout(row_layout)
            sensors_rows.append((hub_combo, sensor_combo))

        add_sensor_btn.clicked.connect(lambda: add_sensor_row())
        # Default one sensor row
        add_sensor_row()
        layout.addLayout(sensors_layout)
        layout.addWidget(add_sensor_btn)

        # Parameters
        parameters_edit = QLineEdit()
        layout.addWidget(QLabel("Parameters:"))
        parameters_edit.setPlaceholderText("Parameters (comma-separated)")
        layout.addWidget(parameters_edit)

        # History size
        history_edit = QLineEdit()
        layout.addWidget(QLabel("Window Size:"))
        history_edit.setPlaceholderText("History size")
        layout.addWidget(history_edit)

        # Output topic
        output_edit = QLineEdit()
        layout.addWidget(QLabel("Output Topic Name:"))
        output_edit.setPlaceholderText("/output_topic")
        layout.addWidget(output_edit)

        # Algorithm selection
        algo_combo = QComboBox()
        algo_combo.addItems(self.algorithms)
        layout.addWidget(algo_combo)

        # Remove button
        remove_btn = QPushButton("Remove Event")
        remove_btn.setProperty("role", "danger")
        remove_btn.clicked.connect(lambda: self.remove_event(event_box))
        layout.addWidget(remove_btn)

        event_box.setLayout(layout)
        self.events_layout.addWidget(event_box)

        self.event_widgets.append({
            "container": event_box,
            "name": event_name_edit,
            "input_topic": input_topic_edit,
            "sensors": sensors_rows,
            "parameters": parameters_edit,
            "history": history_edit,
            "output_topic": output_edit,
            "algorithm": algo_combo
        })

    def remove_event(self, box):
        for i, w in enumerate(self.event_widgets):
            if w["container"] == box:
                self.events_layout.removeWidget(box)
                box.setParent(None)
                self.event_widgets.pop(i)
                break

    def save_yaml(self):
        yaml_data = {"events": {}}
        for w in self.event_widgets:
            name = w["name"].text().strip()
            if not name:
                continue

            input_topic = normalize_topic(w["input_topic"].text())

            sensors_list = []
            for hub_combo, sensor_combo in w["sensors"]:
                hub = hub_combo.currentText()
                sensor = sensor_combo.currentText()
                if hub and sensor:
                    sensors_list.append([hub, sensor])
            sensors_seq = CommentedSeq(sensors_list)
            sensors_seq.fa.set_flow_style()

            parameters = [float(x.strip()) for x in w["parameters"].text().split(",") if x.strip()]
            params_seq = CommentedSeq(parameters)
            params_seq.fa.set_flow_style()

            history_size = int(w["history"].text()) if w["history"].text().isdigit() else 1
            output_topic = normalize_topic(w["output_topic"].text())
            algorithm = w["algorithm"].currentText()

            yaml_data["events"][name] = {
                "input_topic": input_topic,
                "sensors": sensors_seq,
                "parameters": params_seq,
                "history_size": history_size,
                "output_topic": output_topic,
                "algorithm": algorithm
            }

        yaml_path = os.path.join(os.path.expanduser("~"), "exo_stack_resources", "config", "gait_events.yaml")
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)

        yaml = YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(yaml_path, "w") as f:
            yaml.dump(yaml_data, f)

        print(f"Gait events YAML saved at {yaml_path}")

        if self.signal_bus:
            self.signal_bus.gait_events_updated.emit()

    def load_yaml(self):
        """Load YAML file and populate UI fields"""
        yaml_path = os.path.expanduser("~/exo_stack_resources/config/gait_events.yaml")
        if not os.path.exists(yaml_path):
            print(f"[WARN] gait_events.yaml not found at {yaml_path}")
            # Add one blank event
            self.add_event()
            return

        yaml = YAML()
        try:
            with open(yaml_path, "r") as f:
                data = yaml.load(f) or {}
        except Exception as e:
            print(f"[ERROR] Failed to load gait_events.yaml: {e}")
            self.add_event()
            return

        # Clear previous events
        for w in self.event_widgets[:]:
            self.remove_event(w["container"])

        events = data.get("events", {})
        if not events:
            # If no events, add a blank one
            self.add_event()
            return

        for event_name, event_info in events.items():
            self.add_event()
            w = self.event_widgets[-1]  # last added event

            # Set event fields
            w["name"].setText(event_name)
            w["input_topic"].setText(event_info.get("input_topic", "/synced_sensors"))
            w["parameters"].setText(",".join([str(p) for p in event_info.get("parameters", [])]))
            w["history"].setText(str(event_info.get("history_size", 1)))
            w["output_topic"].setText(event_info.get("output_topic", ""))
            w["algorithm"].setCurrentText(event_info.get("algorithm", ""))

            # Clear existing sensor rows
            for hub_combo, sensor_combo in w["sensors"]:
                hub_combo.setParent(None)
                sensor_combo.setParent(None)
            w["sensors"].clear()

            # Add sensor rows from YAML
            for hub_name, sensor_name in event_info.get("sensors", []):
                row_layout = QHBoxLayout()
                hub_combo = QComboBox()
                hub_combo.addItems(self.hubs.keys())
                hub_combo.blockSignals(True)
                if hub_name in self.hubs:
                    hub_combo.setCurrentText(hub_name)
                hub_combo.blockSignals(False)

                sensor_combo = QComboBox()
                sensor_combo.addItems(self.hubs.get(hub_name, {}).get("sensors", []))
                sensor_combo.blockSignals(True)
                if sensor_name in self.hubs.get(hub_name, {}).get("sensors", []):
                    sensor_combo.setCurrentText(sensor_name)
                sensor_combo.blockSignals(False)

                def update_sensors(index, hc=hub_combo, sc=sensor_combo):
                    hub = hc.currentText()
                    sc.blockSignals(True)
                    sc.clear()
                    sc.addItems(self.hubs.get(hub, {}).get("sensors", []))
                    sc.blockSignals(False)

                hub_combo.currentIndexChanged.connect(update_sensors)

                row_layout.addWidget(hub_combo)
                row_layout.addWidget(sensor_combo)
                # Add to the sensors layout of this event
                w["sensors"].append((hub_combo, sensor_combo))
                # Actually add to UI
                # we need a sensors_layout reference per event; here assuming w has "sensors_layout"
                if hasattr(w, "sensors_layout"):
                    w["sensors_layout"].addLayout(row_layout)
                else:
                    # fallback if not stored
                    layout = self.event_widgets[-1]["container"].layout()
                    layout.insertLayout(4, row_layout)  # roughly where sensors are

        print(f"[INFO] Gait events YAML loaded from {yaml_path}")
   
