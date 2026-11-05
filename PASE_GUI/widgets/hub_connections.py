import os
import signal
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QScrollArea, QGroupBox, QCheckBox
)
from PyQt5.QtCore import Qt

class HubConnections(QWidget):
    def __init__(self, title="Hub Connections", width=350, height=250, x=None, y=None, parent=None):
        super().__init__(parent)
        self.port_entries = []
        self.processes = {}  # Key: port, Value: Popen process
        self.connected = False  # Track connection state
        self.width = width
        self.height = height

        # Set fixed size
        self.setFixedSize(self.width, self.height)

        # Optional X,Y position
        if x is not None and y is not None:
            self.move(x, y)

        self.init_ui(title)

    def init_ui(self, title):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5,5,5,5)
        self.setLayout(layout)

        self.group_box = QGroupBox(title)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(5)
        group_layout.setContentsMargins(5,5,5,5)

        # --- Top buttons ---
        buttons_layout = QHBoxLayout()
        self.add_port_btn = QPushButton("Add Port")
        self.add_port_btn.clicked.connect(self.add_port_entry)
        buttons_layout.addWidget(self.add_port_btn)

        self.connect_btn = QPushButton("Connect Hubs")
        self.connect_btn.clicked.connect(self.connect_hubs)
        buttons_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect Hubs")
        self.disconnect_btn.clicked.connect(self.disconnect_hubs)
        buttons_layout.addWidget(self.disconnect_btn)
        group_layout.addLayout(buttons_layout)

        # --- Wireless row ---
        wireless_layout = QHBoxLayout()
        self.wireless_checkbox = QCheckBox("Wireless")
        wireless_layout.addWidget(self.wireless_checkbox)
        self.wireless_port_edit = QLineEdit()
        self.wireless_port_edit.setPlaceholderText("Port number")
        self.wireless_port_edit.setMaximumHeight(25)
        wireless_layout.addWidget(self.wireless_port_edit)
        group_layout.addLayout(wireless_layout)

        # --- USB scroll area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFixedWidth(self.width-20)
        self.scroll_area.setFixedHeight(self.height-100)

        scroll_content = QWidget()
        self.ports_layout = QVBoxLayout()
        self.ports_layout.setAlignment(Qt.AlignTop)
        self.ports_layout.setSpacing(5)
        scroll_content.setLayout(self.ports_layout)
        self.scroll_area.setWidget(scroll_content)
        group_layout.addWidget(self.scroll_area)

        self.group_box.setLayout(group_layout)
        layout.addWidget(self.group_box)

        # Initial USB port
        self.add_port_entry()

    # --- USB port management ---
    def add_port_entry(self):
        row = QHBoxLayout()
        row.setSpacing(5)
        port_edit = QLineEdit()
        port_edit.setPlaceholderText("/dev/ttyUSB0")
        port_edit.setMaximumHeight(25)
        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("role", "danger")
        remove_btn.setMaximumWidth(80)
        remove_btn.setMaximumHeight(25)
        remove_btn.clicked.connect(lambda: self.remove_port_entry(row, port_edit))
        row.addWidget(port_edit)
        row.addWidget(remove_btn)
        self.ports_layout.addLayout(row)
        self.port_entries.append((row, port_edit))

    def remove_port_entry(self, row_layout, port_edit):
        for i in reversed(range(row_layout.count())):
            widget = row_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.ports_layout.removeItem(row_layout)
        self.port_entries = [(r, e) for r, e in self.port_entries if e != port_edit]

    # --- Connect / Disconnect logic ---
    def connect_hubs(self):
        if self.connected:
            print("[INFO] Hubs already connected. No action taken.")
            return

        all_started = True
        any_started = False

        # Wireless
        if self.wireless_checkbox.isChecked():
            wireless_port = self.wireless_port_edit.text().strip()
            if wireless_port:
                cmd = ["ros2", "run", "micro_ros_agent", "micro_ros_agent", "udp4", "--port", wireless_port]
                print(f"[DEBUG] Launch command for Wireless {wireless_port}: {' '.join(cmd)}")
                try:
                    proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
                    self.processes[f"wireless:{wireless_port}"] = proc
                    any_started = True
                except Exception as e:
                    print(f"[ERROR] Failed to start wireless micro-ROS agent on port {wireless_port}: {e}")
                    all_started = False
            else:
                all_started = False

        # USB ports
        for _, port_edit in self.port_entries:
            port_name = port_edit.text().strip()
            if not port_name or port_name in self.processes:
                continue
            cmd = ["ros2", "run", "micro_ros_agent", "micro_ros_agent", "serial", "--dev", port_name, "-b", "115200"]
            # cmd=["ros2", "run", "exo_stack", port_name]
            print(f"[DEBUG] Launch command for {port_name}: {' '.join(cmd)}")
            try:
                # proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
                proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
                self.processes[port_name] = proc
                any_started = True
            except Exception as e:
                print(f"[ERROR] Failed to start micro-ROS agent for {port_name}: {e}")
                all_started = False

        if any_started and all_started:
            self.connect_btn.setStyleSheet("background-color: green; color: white;")
            self.connected = True
        else:
            self.connect_btn.setStyleSheet("")
            self.connected = False

    def disconnect_hubs(self):
        for port, proc in self.processes.items():
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGINT)
                proc.wait(timeout=5)
            except Exception as e:
                print(f"Failed to stop {port}: {e}")
        self.processes.clear()
        self.connect_btn.setStyleSheet("")
        self.connected = False
