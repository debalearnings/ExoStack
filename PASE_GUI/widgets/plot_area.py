import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QMenu, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from widgets.plot_widget import RosPlotWidget


class PlotArea(QWidget):
    """
    Main container that manages multiple RosPlotWidget instances.
    Supports dynamic splitting, layout save/load, and pause functionality.
    """

    def __init__(self):
        super().__init__()
        self.root_splitter = QSplitter(Qt.Horizontal)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.root_splitter)
        self.setLayout(self.layout)

        # Start with one blank plot by default
        first_plot = RosPlotWidget()
        self.root_splitter.addWidget(first_plot)
        self._connect_plot_signals(first_plot)

        # paused state
        self._paused = False

    # ------------------- Add / Remove -------------------

    def add_blank_plot(self):
        """Add a blank RosPlotWidget to the layout."""
        new_plot = RosPlotWidget()
        self.root_splitter.addWidget(new_plot)
        self._connect_plot_signals(new_plot)

    def add_plot(self, topic, field, msg_type=None):
        """Add a RosPlotWidget pre-subscribed to topic+field."""
        print(f"Adding plot for topic={topic}, field={field}, msg_type={msg_type}")
        new_plot = RosPlotWidget(title=f"{topic}:{field}")
        new_plot.add_subscription(topic, field)
        self.root_splitter.addWidget(new_plot)
        self._connect_plot_signals(new_plot)

    def _connect_plot_signals(self, plot):
        """Connect control signals emitted by RosPlotWidget."""
        if hasattr(plot, "request_split_vertical"):
            plot.request_split_vertical.connect(self._split_vertical)
        if hasattr(plot, "request_split_horizontal"):
            plot.request_split_horizontal.connect(self._split_horizontal)
        if hasattr(plot, "request_remove"):
            plot.request_remove.connect(self._remove_plot)

    # ------------------- Split Actions -------------------

    def _split_vertical(self, plot):
        """Split selected plot vertically into two."""
        parent = plot.parent()
        if not isinstance(parent, QSplitter):
            return

        new_splitter = QSplitter(Qt.Vertical)
        parent.replaceWidget(parent.indexOf(plot), new_splitter)
        new_splitter.addWidget(plot)

        new_plot = RosPlotWidget()
        self._connect_plot_signals(new_plot)
        new_splitter.addWidget(new_plot)

    def _split_horizontal(self, plot):
        """Split selected plot horizontally into two."""
        parent = plot.parent()
        if not isinstance(parent, QSplitter):
            return

        new_splitter = QSplitter(Qt.Horizontal)
        parent.replaceWidget(parent.indexOf(plot), new_splitter)
        new_splitter.addWidget(plot)

        new_plot = RosPlotWidget()
        self._connect_plot_signals(new_plot)
        new_splitter.addWidget(new_plot)

    def _remove_plot(self, plot):
        """Remove the selected plot widget."""
        parent = plot.parent()
        if isinstance(parent, QSplitter):
            parent_index = parent.indexOf(plot)
            plot.deleteLater()

            # remove widget at that index (if still exists)
            try:
                w = parent.widget(parent_index)
                if w:
                    w.deleteLater()
            except Exception:
                pass

            # If splitter now has only one widget, collapse up
            if parent.count() == 1:
                remaining = parent.widget(0)
                grandparent = parent.parent()
                if isinstance(grandparent, QSplitter):
                    gp_index = grandparent.indexOf(parent)
                    parent.hide()
                    grandparent.insertWidget(gp_index, remaining)
                    parent.deleteLater()

    # ------------------- Pause Toggle -------------------

    def toggle_pause(self, pause_state: bool = None):
        """
        Toggle pause if pause_state is None. Otherwise set to provided boolean.
        True = pause plotting (stop updates), False = resume.
        """
        if pause_state is None:
            self._paused = not self._paused
        else:
            self._paused = bool(pause_state)

        # propagate to all RosPlotWidget children
        for plot in self.findChildren(RosPlotWidget):
            if hasattr(plot, "set_paused"):
                plot.set_paused(self._paused)

        print("[INFO] Plotting paused" if self._paused else "[INFO] Plotting resumed")

    # ------------------- Layout Save / Load -------------------

    def save_layout(self, filepath: str = None):
        """
        Save layout to filepath. If filepath missing, open a save dialog.
        Ensures .json extension.
        """
        if not filepath:
            path, _ = QFileDialog.getSaveFileName(self, "Save Layout", "", "JSON Files (*.json)")
            if not path:
                return
            filepath = path

        if not filepath.lower().endswith(".json"):
            filepath += ".json"

        layout_dict = self._serialize_splitter(self.root_splitter)
        try:
            with open(filepath, "w") as f:
                json.dump(layout_dict, f, indent=2)
            print(f"[INFO] Layout saved to {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save layout:\n{e}")

    def load_layout(self, filepath: str = None):
        """
        Load layout from filepath. If filepath missing, open an open dialog.
        """
        if not filepath:
            path, _ = QFileDialog.getOpenFileName(self, "Load Layout", "", "JSON Files (*.json)")
            if not path:
                return
            filepath = path

        try:
            with open(filepath, "r") as f:
                layout_dict = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to open layout:\n{e}")
            return

        # Clear existing root_splitter widgets
        while self.root_splitter.count():
            w = self.root_splitter.widget(0)
            self.root_splitter.removeWidget(w)
            w.setParent(None)
            try:
                w.deleteLater()
            except Exception:
                pass

        # Build new splitter structure into root_splitter
        self._deserialize_splitter(layout_dict, self.root_splitter)
        print(f"[INFO] Layout loaded from {filepath}")

    # ------------------- Serialization helpers -------------------

    def _serialize_splitter(self, splitter: QSplitter):
        """
        Recursively serialize a splitter. Store:
        - type: 'splitter'
        - orientation: 'horizontal' or 'vertical'
        - sizes: list of ints (splitter.sizes())
        - children: list (either child splitter dicts or plot dicts)
        """
        data = {
            "type": "splitter",
            "orientation": "horizontal" if splitter.orientation() == Qt.Horizontal else "vertical",
            "sizes": splitter.sizes(),
            "children": [],
        }

        for i in range(splitter.count()):
            w = splitter.widget(i)
            if isinstance(w, RosPlotWidget):
                plot_data = w.serialize()
                plot_data["type"] = "plot"
                data["children"].append(plot_data)
            elif isinstance(w, QSplitter):
                data["children"].append(self._serialize_splitter(w))
            else:
                data["children"].append({"type": "empty"})
        return data

    def _deserialize_splitter(self, data: dict, parent_splitter: QSplitter):
        """
        Given a serialized splitter dict, populate parent_splitter with the described children.
        """
        orientation = data.get("orientation", "horizontal")
        parent_splitter.setOrientation(Qt.Horizontal if orientation == "horizontal" else Qt.Vertical)

        children = data.get("children", [])
        for child in children:
            ctype = child.get("type")
            if ctype == "plot":
                plot = RosPlotWidget()
                plot.deserialize(child)
                parent_splitter.addWidget(plot)
                self._connect_plot_signals(plot)
            elif ctype == "splitter":
                sub_splitter = QSplitter()
                parent_splitter.addWidget(sub_splitter)
                self._deserialize_splitter(child, sub_splitter)
            else:
                blank = RosPlotWidget()
                parent_splitter.addWidget(blank)
                self._connect_plot_signals(blank)

        # Restore sizes
        sizes = data.get("sizes")
        if isinstance(sizes, list) and len(sizes) == parent_splitter.count():
            try:
                parent_splitter.setSizes([int(s) for s in sizes])
            except Exception:
                pass

    # ------------------- Context menu -------------------

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Add Blank Plot", self.add_blank_plot)
        menu.exec_(event.globalPos())
