import os
import signal
import subprocess
import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

class Synchronizer(QWidget):
    def __init__(self, title="Synchronizer", width=200, height=150, x=None, y=None, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.setFixedSize(self.width, self.height)

        self.process = None
        self.running = False  # Track sync state

        if x is not None and y is not None:
            self.move(x, y)

        self.init_ui(title)

    def init_ui(self, title):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(5,5,5,5)
        self.setLayout(layout)

        self.group_box = QGroupBox(title)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(5)
        group_layout.setContentsMargins(5,5,5,5)
        self.group_box.setLayout(group_layout)
        layout.addWidget(self.group_box)

        # --- Start Sync Button ---
        self.start_btn = QPushButton("Start Sync")
        self.start_btn.clicked.connect(self.start_sync)
        group_layout.addWidget(self.start_btn)

        # --- Stop Sync Button ---
        self.stop_btn = QPushButton("Stop Sync")
        self.stop_btn.clicked.connect(self.stop_sync)
        group_layout.addWidget(self.stop_btn)

        # --- Refresh Sync Button (image) ---
        self.refresh_btn = QPushButton()
        icon_size = QSize(32, 32)
        self.refresh_btn.setIcon(QIcon("resources/REFRESH_BUTTON.jpg"))
        self.refresh_btn.setIconSize(icon_size)
        self.refresh_btn.setFixedSize(icon_size)
        self.refresh_btn.setStyleSheet("QPushButton{border:none;background:transparent;border-radius:8px;padding:0px;} QPushButton:hover{background:#232E3B;}")
        self.refresh_btn.clicked.connect(self.refresh_sync)

        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        refresh_layout.addWidget(self.refresh_btn)
        refresh_layout.addStretch()
        group_layout.addLayout(refresh_layout)

    # --- Start Sync ---
    def start_sync(self):
        if self.running:
            print("[INFO] Sync already running. No action taken.")
            return
        try:
            cmd = ["ros2", "run", "exo_stack", "sync"]
            print(f"[DEBUG] Launch command: {' '.join(cmd)}")
            self.process = subprocess.Popen(cmd, preexec_fn=os.setsid)
            self.running = True
            self.start_btn.setStyleSheet("background-color: green; color: white;")
            print("[INFO] Sync started successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to start sync: {e}")
            self.running = False
            self.start_btn.setStyleSheet("")
            self.process = None

    # --- Stop Sync (same as Hub Disconnect) ---
    def stop_sync(self):
        if not self.running or not self.process:
            print("[INFO] Sync not running. No action taken.")
            return

        try:
            print(f"[DEBUG] Sending SIGINT to sync process group: {self.process.pid}")
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            self.process.wait(timeout=5)
            print("[INFO] Sync stopped successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to stop sync: {e}")
        finally:
            self.process = None
            self.running = False
            self.start_btn.setStyleSheet("")

    # --- Refresh Sync ---
    def refresh_sync(self):
        if not self.running:
            print("[INFO] Sync not running. Cannot refresh.")
            return
        self.stop_sync()
        time.sleep(1)
        self.start_sync()
