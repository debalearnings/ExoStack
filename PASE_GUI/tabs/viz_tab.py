from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from widgets.plot_area import PlotArea
from widgets.topic_explorer import TopicExplorer


class VisualizationTab(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)

        # ----------- Toolbar Section -----------
        toolbar = QHBoxLayout()
        self.btn_save = QPushButton("💾 Save Layout")
        self.btn_load = QPushButton("📂 Load Layout")
        self.btn_toggle = QPushButton("▶/⏸")
        self.btn_toggle.setCheckable(True)

        # Style (optional)
        for btn in [self.btn_save, self.btn_load, self.btn_toggle]:
            btn.setMinimumWidth(120)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1C2530;
                    color: #E8EEF4;
                    border: 1px solid #3A4A5E;
                    border-radius: 8px;
                    padding: 7px 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #232E3B;
                    border: 1px solid #2DD4BF;
                    color: #54E8D6;
                }
                QPushButton:checked {
                    background-color: #15786E;
                    border: 1px solid #2DD4BF;
                    color: #FFFFFF;
                }
            """)

        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_toggle)
        toolbar.addStretch(1)
        main_layout.addLayout(toolbar)

        # ----------- Content Section -----------
        content_layout = QHBoxLayout()
        self.topic_explorer = TopicExplorer()
        self.plot_area = PlotArea()
        content_layout.addWidget(self.topic_explorer, 1)
        content_layout.addWidget(self.plot_area, 3)
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        # ----------- Button Connections -----------
        self.btn_save.clicked.connect(self.save_layout)
        self.btn_load.clicked.connect(self.load_layout)
        self.btn_toggle.toggled.connect(self.toggle_plotting)

        # ----------- Plot Request Connection -----------
        self.topic_explorer.plot_requested.connect(self.handle_plot_request)

    # ------------------- Button Actions -------------------

    def save_layout(self):
        """Save current plot layout to a JSON file."""
        try:
            filepath, _ = QFileDialog.getSaveFileName(self, "Save Layout", "", "JSON Files (*.json)")
            if not filepath:
                return
            self.plot_area.save_layout(filepath)
            QMessageBox.information(self, "Layout Saved", f"Layout successfully saved to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save layout:\n{e}")

    def load_layout(self):
        """Load plot layout from a JSON file."""
        try:
            filepath, _ = QFileDialog.getOpenFileName(self, "Load Layout", "", "JSON Files (*.json)")
            if not filepath:
                return
            self.plot_area.load_layout(filepath)
            QMessageBox.information(self, "Layout Loaded", f"Layout successfully loaded from:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load layout:\n{e}")

    def toggle_plotting(self, checked):
        """Pause/Resume plotting on toggle."""
        self.plot_area.toggle_pause()
        if checked:
            self.btn_toggle.setText("▶/⏸")
        else:
            self.btn_toggle.setText("▶/⏸")

    # ------------------- Plot Request -------------------

    def handle_plot_request(self, topic, field, msg_type):
        self.plot_area.add_plot(topic, field, msg_type)
