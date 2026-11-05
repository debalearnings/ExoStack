# main.py (updated to integrate with your existing Exosuit GUI structure)

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget

# Disable Qt debug spam
os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"

# --- Import tabs ---
from tabs.config_tab import ConfigTab
from tabs.launch_tab import LaunchTab
from tabs.viz_tab import VisualizationTab  # this will point to our new visualization module

# --- Import shared signal bus ---
from signal_bus import SignalBus

# --- Visual theme (cosmetic only) ---
import theme


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExoStack · PACE Console")
        self.resize(1500, 900)

        # Create the shared signal bus (so all tabs can communicate)
        self.signal_bus = SignalBus()

        # Initialize and add tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(ConfigTab(self.signal_bus), "Configuration")
        self.tabs.addTab(LaunchTab(self.signal_bus), "Launch")
        self.tabs.addTab(VisualizationTab(), "Visualization")

        self.setCentralWidget(self.tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    theme.apply_theme(app)          # <-- global look & feel
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
