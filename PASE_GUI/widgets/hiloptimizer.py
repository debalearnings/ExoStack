import os
import signal
import subprocess
import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

class HILOptimization(QWidget):
    def __init__(self, title="HIL Optimization", width=200, height=150, x=None, y=None, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.setFixedSize(self.width, self.height)

        self.process = None
        self.running = False  # Track optimization state

        if x is not None and y is not None:
            self.move(x, y)

        self.init_ui(title)

    def init_ui(self, title):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        self.group_box = QGroupBox(title)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(5)
        group_layout.setContentsMargins(5, 5, 5, 5)
        self.group_box.setLayout(group_layout)
        layout.addWidget(self.group_box)

        # --- Start Optimization Button ---
        self.start_btn = QPushButton("Start Optimization")
        self.start_btn.clicked.connect(self.start_optimization)
        group_layout.addWidget(self.start_btn)

        # --- Stop Optimization Button ---
        self.stop_btn = QPushButton("Stop Optimization")
        self.stop_btn.clicked.connect(self.stop_optimization)
        group_layout.addWidget(self.stop_btn)

        # --- Reset Optimization Button (image) ---
        self.reset_btn = QPushButton()
        icon_size = QSize(32, 32)
        self.reset_btn.setIcon(QIcon("resources/REFRESH_BUTTON.jpg"))
        self.reset_btn.setIconSize(icon_size)
        self.reset_btn.setFixedSize(icon_size)
        self.reset_btn.setStyleSheet("QPushButton{border:none;background:transparent;border-radius:8px;padding:0px;} QPushButton:hover{background:#232E3B;}")
        self.reset_btn.clicked.connect(self.reset_optimization)

        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        reset_layout.addWidget(self.reset_btn)
        reset_layout.addStretch()
        group_layout.addLayout(reset_layout)

    # --- Start Optimization ---
    def start_optimization(self):
        if self.running:
            print("[INFO] HIL Optimization already running. No action taken.")
            return
        try:
            cmd = ["ros2", "launch", "exo_stack", "hil_launch.py"]
            print(f"[DEBUG] Launch command: {' '.join(cmd)}")
            self.process = subprocess.Popen(cmd, preexec_fn=os.setsid)
            self.running = True
            self.start_btn.setStyleSheet("background-color: green; color: white;")
            print("[INFO] HIL Optimization started successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to start HIL Optimization: {e}")
            self.running = False
            self.start_btn.setStyleSheet("")
            self.process = None

    # --- Stop Optimization ---
    def stop_optimization(self):
        if not self.running or not self.process:
            print("[INFO] HIL Optimization not running. No action taken.")
            return

        try:
            print(f"[DEBUG] Sending SIGINT to optimization process group: {self.process.pid}")
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            self.process.wait(timeout=5)
            print("[INFO] HIL Optimization stopped successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to stop HIL Optimization: {e}")
        finally:
            self.process = None
            self.running = False
            self.start_btn.setStyleSheet("")

    # --- Reset Optimization ---
    def reset_optimization(self):
        if not self.running:
            print("[INFO] HIL Optimization not running. Cannot reset.")
            return
        self.stop_optimization()
        time.sleep(1)
        self.start_optimization()
