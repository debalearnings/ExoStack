# widgets/plot_widget.py
import time
import itertools
import threading
import queue
from collections import deque, defaultdict
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QMenu, QLabel, QMessageBox, QColorDialog
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QObject, QEvent
from PyQt5.QtGui import QColor
import pyqtgraph as pg
from widgets.ros_helpers import create_ros_subscriber, get_ros2_topics, synced_sensor_index_map
import random
import json
import re


# ---------- helper for legend label right-click -----------
class LegendLabelEventFilter(QObject):
    def __init__(self, parent_widget, key):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.key = key

    def eventFilter(self, obj, event):
        # right-click on the legend label triggers color picker
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            self.parent_widget._show_color_picker_for_key(self.key)
            return True
        return False


class RosPlotWidget(QWidget):
    request_split_vertical = pyqtSignal(QWidget)
    request_split_horizontal = pyqtSignal(QWidget)
    request_remove = pyqtSignal(QWidget)

    _global_color_offset = 0

    def __init__(self, topic=None, field=None, msg_type=None):
        super().__init__()
        # thread-safety primitives
        self._lock = threading.Lock()
        # msg queues: each (topic,field) maps to a queue.Queue of received msgs (raw)
        self._msg_queues = defaultdict(queue.Queue)

        # state
        self.topics_info = {}     # (topic, field) -> (msg_type_str, subscription_obj)
        # data_buffers store (timestamps_deque, values_deque) — timestamps are float seconds (msg gen time)
        self.data_buffers = defaultdict(lambda: (deque(maxlen=1000), deque(maxlen=1000)))
        self.event_timestamps = defaultdict(lambda: deque(maxlen=1000))  # for event markers (timestamps in sec)
        self.modes = {}            # (topic, field) -> "continuous" / "event"
        self.curves = {}           # (topic, field) -> pg.PlotDataItem
        self.event_lines = {}      # (topic, field) -> list of pg.InfiniteLine
        self.colors = {}           # (topic, field) -> QColor
        self.window_duration = 10.0
        self.start_time = None     # arrival time of the first sample (shared origin)
        self.paused = False

        # UI and timer
        self.init_ui()
        self.setAcceptDrops(True)
        self.refresh_rate_hz = 30
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot_display)
        self.timer.start(int(1000 / self.refresh_rate_hz))

        # color palette
        self._base_colors = [
            (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40),
            (148, 103, 189), (140, 86, 75), (227, 119, 194), (127, 127, 127),
            (188, 189, 34), (23, 190, 207)
        ]
        offset = RosPlotWidget._global_color_offset % len(self._base_colors)
        rotated = self._base_colors[offset:] + self._base_colors[:offset]
        RosPlotWidget._global_color_offset = (
            RosPlotWidget._global_color_offset + random.randint(2, 5)
        ) % len(self._base_colors)
        self._color_cycle = itertools.cycle(rotated)
        self._used_colors = {}
        self._legend_label_to_key = {}

        # background reader thread (daemon)
        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

        # if pre-specified subscription requested
        if topic and field and msg_type:
            self.add_subscription(topic, field, msg_type)

    # ------------------- UI -------------------
    def init_ui(self):
        layout = QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setBackground('black')
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        try:
            self.legend.setLabelTextColor('w')
        except Exception:
            pass
        self.label = QLabel("Drop a topic field here", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.update_title()

    def update_title(self):
        # combine continuous and event keys for title
        keys = list(self.curves.keys()) + list(self.event_timestamps.keys())
        if keys:
            fields_str = " , ".join([self._format_curve_label(t, f) for (t, f) in keys])
            self.plot_widget.setTitle(fields_str, color='w', size='10pt')
            self.label.hide()
            self.legend.setVisible(True)
        else:
            self.plot_widget.setTitle("Empty Plot", color='gray', size='9pt')
            self.label.show()
            self.legend.setVisible(False)

    def _format_curve_label(self, topic, field):
        try:
            if topic == "/synced_sensors" and field.startswith("data[") and "]" in field:
                idx = int(field.split("[", 1)[1].split("]", 1)[0])
                for (hub, sensor), index in synced_sensor_index_map.items():
                    if index == idx:
                        return f"{hub}:{sensor}"
        except Exception:
            pass
        return f"{topic}:{field}"

    def _get_unique_color(self, key):
        if key not in self._used_colors:
            base_color = next(self._color_cycle)
            if len(self._used_colors) >= len(self._base_colors):
                r, g, b = base_color
                base_color = (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255))
            qcol = QColor(*base_color)
            self._used_colors[key] = qcol
        return self._used_colors[key]

    # ------------------- Background reader thread -------------------
    def _reader_loop(self):
        """
        Background thread that consumes raw messages from per-topic queues,
        timestamps each by arrival time, and writes into the
        timestamp-aligned data_buffers or event_timestamps under lock.
        """
        while self._running:
            processed_any = False
            # iterate over a snapshot of queues to avoid locking long
            keys = list(self._msg_queues.keys())
            for key in keys:
                q = self._msg_queues.get(key)
                if q is None:
                    continue
                try:
                    # drain the queue (process all available without blocking)
                    while True:
                        msg = q.get_nowait()
                        processed_any = True
                        self._process_raw_message(key, msg)
                except queue.Empty:
                    pass
            if not processed_any:
                # avoid busy loop; sleep briefly
                time.sleep(0.005)

    def _process_raw_message(self, key, msg):
        """
        Convert raw msg to (timestamp, value) and push to buffers under lock.
        key: (topic, field)
        """
        topic, field = key
        # Timestamp every sample by ARRIVAL time (wall clock). We deliberately do
        # NOT use header.stamp: different publishers stamp on different clocks
        # (e.g. the hub emulators stamp seconds-since-boot, other nodes use ROS
        # time), which would place curves on incompatible time axes and make them
        # impossible to overlay. Arrival time gives every topic — header-stamped
        # or not — one common time base so they all plot together seamlessly.
        ts = time.time()

        # set reference start_time as the first sample's arrival time
        with self._lock:
            if self.start_time is None:
                self.start_time = ts

        rel_t = ts - self.start_time

        # extract numeric value (same as previous extract_field) — but do it here once
        val = None
        try:
            val = self._extract_field_from_msg_object(msg, field)
        except Exception:
            val = None

        # write to appropriate buffer under lock
        with self._lock:
            mode = self.modes.get(key, "continuous")
            if mode == "continuous":
                ts_deque, val_deque = self.data_buffers[key]
                ts_deque.append(rel_t)
                val_deque.append(val)
                # trim by window duration
                while ts_deque and (rel_t - ts_deque[0]) > self.window_duration:
                    ts_deque.popleft(); val_deque.popleft()
            else:
                self.event_timestamps[key].append(rel_t)
                # trim
                while self.event_timestamps[key] and (rel_t - self.event_timestamps[key][0]) > self.window_duration:
                    self.event_timestamps[key].popleft()

    def _extract_field_from_msg_object(self, msg, field_path):
        """
        Extract a scalar value from a ROS2 message given a field path.

        Supports arbitrarily nested attribute access and array indexing at any
        segment of the path, e.g.:
            "angle_min"                  -> msg.angle_min
            "header.stamp.sec"           -> msg.header.stamp.sec
            "intensities[10]"            -> msg.intensities[10]
            "data[3]"                    -> msg.data[3]            (back-compat)
            "poses[2].pose.position.x"   -> msg.poses[2].pose.position.x
        Returns None if any attribute is missing or any index is out of range,
        so a bad/transient path simply yields no point rather than raising.
        """
        value = msg
        for token in field_path.split('.'):
            if not token:
                continue
            # a token looks like "name", "name[2]" or even "name[2][3]"
            name = token.split('[', 1)[0]
            if name:
                value = getattr(value, name, None)
                if value is None:
                    return None
            # apply any [i] indices contained in this token, left to right
            for idx_str in re.findall(r'\[\s*(-?\d+)\s*\]', token):
                try:
                    value = value[int(idx_str)]
                except (IndexError, KeyError, TypeError):
                    return None
        return value

    # ------------------- Subscription / plotting -------------------
    def add_subscription(self, topic, field, msg_type, mode="continuous"):
        key = (topic, field)
        if key in self.topics_info:
            print(f"[INFO] Already subscribed to {topic}:{field}")
            return
        print(f"[INFO] Subscribing to {topic}:{field} as {mode}")

        try:
            # create subscriber; callback should be as fast as possible: enqueue message
            def _enqueue(msg, t=topic, f=field):
                # put raw message object into per-key queue
                try:
                    self._msg_queues[(t, f)].put_nowait(msg)
                except Exception:
                    # fallback: block put
                    try:
                        self._msg_queues[(t, f)].put(msg, timeout=0.01)
                    except Exception:
                        pass

            sub = create_ros_subscriber(
                topic, msg_type,
                lambda msg, t=topic, f=field: _enqueue(msg, t, f)
            )
            self.topics_info[key] = (msg_type, sub)

            # initialize mode under lock
            with self._lock:
                self.modes[key] = mode
                color_q = self._get_unique_color(key)
                self.colors[key] = color_q

                if mode == "continuous":
                    pen = pg.mkPen(color_q, width=2)
                    curve = self.plot_widget.plot(pen=pen)
                    self.curves[key] = curve
                    label_text = self._format_curve_label(topic, field)
                    try:
                        legend_item = self.legend.addItem(curve, label_text)
                        self._legend_label_to_key[label_text] = key
                        if hasattr(legend_item, "labelItem"):
                            legend_item.labelItem.installEventFilter(LegendLabelEventFilter(self, key))
                    except Exception:
                        pass
                else:
                    # event mode
                    self.event_timestamps[key] = deque(maxlen=1000)
                    self.event_lines[key] = []

            self.update_title()
        except Exception as e:
            QMessageBox.critical(self, "ROS2 Subscription Error",
                                 f"Failed to subscribe to topic '{topic}':\n{str(e)}")

    def callback(self, msg, topic, field):
        """
        This method remains for compatibility — but actual ROS callbacks enqueue via
        add_subscription's local enqueuer. We keep this here in case other code calls it.
        """
        try:
            self._msg_queues[(topic, field)].put_nowait(msg)
        except Exception:
            try:
                self._msg_queues[(topic, field)].put(msg, timeout=0.01)
            except Exception:
                pass

    # ------------------- Rendering -------------------
    def update_plot_display(self):
        """
        Main GUI-thread render loop. Reads from data_buffers and event_timestamps
        under lock, and updates pyqtgraph items.
        """
        if self.paused or self.start_time is None:
            return

        with self._lock:
            # All data is arrival-timestamped, so the window simply tracks real
            # elapsed time from the first sample — one clock for every topic.
            now = time.time() - self.start_time

            # continuous curves
            for (topic, field), (ts, vals) in list(self.data_buffers.items()):
                # trim stale points (already trimmed in reader but double-check)
                while ts and (now - ts[0]) > self.window_duration:
                    ts.popleft(); vals.popleft()
                if (topic, field) in self.curves:
                    # create copies to avoid concurrent modification
                    xs = list(ts)
                    ys = list(vals)
                    self.curves[(topic, field)].setData(xs, ys)

            # event markers: remove previous lines and re-draw those in window
            for key, timestamps in list(self.event_timestamps.items()):
                # clear previous lines
                lines = self.event_lines.get(key, [])
                for line in lines:
                    try:
                        self.plot_widget.removeItem(line)
                    except Exception:
                        pass
                self.event_lines[key] = []

                color = self.colors.get(key, QColor(255, 255, 255))
                pen = pg.mkPen(color, style=Qt.DashLine, width=2)
                for ts in timestamps:
                    if now - ts <= self.window_duration:
                        # InfiniteLine placed at x=ts
                        line = pg.InfiniteLine(pos=ts, angle=90, pen=pen)
                        self.plot_widget.addItem(line)
                        self.event_lines[key].append(line)

            # auto Y range
            all_vals = [v for _, (_, v) in self.data_buffers.items() for v in v]
            if not all_vals:
                # keep a reasonable default range
                self.plot_widget.setYRange(0, 1)
            else:
                ymin, ymax = min(all_vals), max(all_vals)
                if ymin == ymax:
                    ymin -= 0.1; ymax += 0.1
                self.plot_widget.setYRange(ymin, ymax, padding=0.1)

            # rolling X range
            self.plot_widget.setXRange(max(0, now - self.window_duration), now, padding=0)

    # ------------------- Mode switching -------------------
    def set_mode(self, topic, field, mode):
        key = (topic, field)
        with self._lock:
            if key not in self.modes:
                return
            if mode == self.modes[key]:
                return
            print(f"[INFO] Switching {topic}:{field} to {mode} mode")
            self.modes[key] = mode
            if mode == "continuous":
                color = self.colors.get(key, QColor(255, 255, 255))
                pen = pg.mkPen(color, width=2)
                curve = self.plot_widget.plot(pen=pen)
                self.curves[key] = curve
                # move any event timestamps into data buffer? keep separate — start fresh
                if key in self.event_lines:
                    for line in self.event_lines[key]:
                        try:
                            self.plot_widget.removeItem(line)
                        except Exception:
                            pass
                    self.event_lines[key] = []
                self.event_timestamps.pop(key, None)
            else:  # switch to event
                if key in self.curves:
                    try:
                        self.plot_widget.removeItem(self.curves[key])
                    except Exception:
                        pass
                    del self.curves[key]
                self.event_timestamps[key] = deque(maxlen=1000)
                self.event_lines[key] = []

    # ------------------- Legend / color picker -------------------
    def _show_color_picker_for_key(self, key):
        try:
            current_color = self.colors.get(key, QColor(255, 255, 255))
            color = QColorDialog.getColor(current_color, self, "Choose curve color")
            if color.isValid():
                with self._lock:
                    self.colors[key] = color
                    self._used_colors[key] = color
                    if key in self.curves:
                        self.curves[key].setPen(pg.mkPen(color, width=2))
        except Exception as e:
            print(f"[WARN] Could not change color for {key}: {e}")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # color submenu
        curve_menu = QMenu("Change curve color", self)
        if not self.colors:
            curve_menu.addAction("No curves available").setEnabled(False)
        else:
            for key in list(self.colors.keys()):
                topic, field = key
                label = self._format_curve_label(topic, field)
                act = curve_menu.addAction(label)
                act.triggered.connect(lambda checked=False, k=key: self._show_color_picker_for_key(k))
        menu.addMenu(curve_menu)

        # mode submenu
        mode_menu = QMenu("Set mode", self)
        for key in list(self.topics_info.keys()):
            topic, field = key
            label = self._format_curve_label(topic, field)
            sub_menu = mode_menu.addMenu(label)
            sub_menu.addAction("Continuous", lambda checked=False, k=key: self.set_mode(k[0], k[1], "continuous"))
            sub_menu.addAction("Event", lambda checked=False, k=key: self.set_mode(k[0], k[1], "event"))
        menu.addMenu(mode_menu)

        menu.addSeparator()
        menu.addAction("Split Vertically", lambda: self.request_split_vertical.emit(self))
        menu.addAction("Split Horizontally", lambda: self.request_split_horizontal.emit(self))
        menu.addSeparator()
        menu.addAction("Remove Plot", lambda: self.request_remove.emit(self))
        menu.exec_(event.globalPos())

    def set_paused(self, paused: bool):
        self.paused = bool(paused)

    # ------------------- Serialization -------------------
    def serialize(self):
        topics = []
        with self._lock:
            for (t, f), (msg_type, _sub) in self.topics_info.items():
                color = self.colors.get((t, f))
                color_hex = color.name() if isinstance(color, QColor) else None
                mode = self.modes.get((t, f), "continuous")
                topics.append({"topic": t, "field": f, "msg_type": msg_type,
                               "color": color_hex, "mode": mode})
        return {"type": "plot", "topics": topics, "window_duration": self.window_duration}

    def deserialize(self, data):
        for entry in data.get("topics", []):
            t = entry.get("topic")
            f = entry.get("field")
            mt = entry.get("msg_type")
            color_hex = entry.get("color")
            mode = entry.get("mode", "continuous")
            if t and f and mt:
                self.add_subscription(t, f, mt, mode)
                if color_hex:
                    try:
                        qcol = QColor(color_hex)
                        with self._lock:
                            self.colors[(t, f)] = qcol
                            self._used_colors[(t, f)] = qcol
                            if (t, f) in self.curves:
                                self.curves[(t, f)].setPen(pg.mkPen(qcol, width=2))
                    except Exception:
                        pass

    # ------------------- Drag & drop -------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        text = event.mimeData().text().strip()
        if "|" in text:
            parts = text.split("|")
            topic = parts[0]
            field = parts[1] if len(parts) > 1 else ""
            # optional mode at third part (if topic explorer includes it)
            mode = parts[2] if len(parts) > 2 else "continuous"
            topics = dict(get_ros2_topics())
            msg_type = topics.get(topic)
            if not msg_type:
                QMessageBox.warning(self, "Unknown Topic", f"Could not determine message type for {topic}")
                return
            self.add_subscription(topic, field, msg_type, mode)
            self.force_sync_to_latest()
        else:
            print("[WARN] Drop format invalid. Expected '<topic>|<field>'")
        event.acceptProposedAction()

    def force_sync_to_latest(self):
        with self._lock:
            if self.start_time is None:
                return
            now = time.time() - self.start_time
            for (topic, field), (ts, vals) in self.data_buffers.items():
                while ts and (now - ts[0]) > self.window_duration:
                    ts.popleft(); vals.popleft()
                if (topic, field) in self.curves:
                    self.curves[(topic, field)].setData(list(ts), list(vals))
            self.plot_widget.setXRange(max(0, now - self.window_duration), now, padding=0)

    def extract_field(self, msg, field_path):
        """
        Public extract method kept for compatibility. Uses same logic as internal extractor.
        """
        try:
            return self._extract_field_from_msg_object(msg, field_path)
        except Exception as e:
            print(f"[WARN] Failed to extract field {field_path}: {e}")
            return None

    # ------------------- cleanup -------------------
    def closeEvent(self, event):
        # stop background thread
        self._running = False
        try:
            self._reader_thread.join(timeout=0.1)
        except Exception:
            pass
        super().closeEvent(event)