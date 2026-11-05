from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import pyqtSignal, Qt


class TopicTreePanel(QWidget):
    # Signals
    plot_requested = pyqtSignal(str, str, object)
    refresh_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.refresh_btn = QPushButton("🔄 Refresh Topics")
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["ROS2 Topics"])
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def _on_refresh_clicked(self):
        """Emit signal when refresh button clicked."""
        self.refresh_requested.emit()

    def update_topics(self, topic_list):
        """Clear and repopulate the tree with new topics."""
        self.tree.clear()
        for topic_name, msg_type in sorted(topic_list):
            item = QTreeWidgetItem([topic_name])
            item.setData(0, Qt.UserRole, (topic_name, msg_type, None))
            self.tree.addTopLevelItem(item)
        self.tree.expandAll()

    def _on_item_double_clicked(self, item, column):
        """Emit plot request when user double-clicks a topic."""
        data = item.data(0, Qt.UserRole)
        if data:
            topic_name, msg_type, field_path = data
            self.plot_requested.emit(topic_name, msg_type, field_path)
