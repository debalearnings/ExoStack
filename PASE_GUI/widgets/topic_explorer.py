from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PyQt5.QtCore import pyqtSignal, Qt, QMimeData
from PyQt5.QtGui import QDrag
from widgets.ros_helpers import get_ros2_topics, synced_sensor_index_map
from rosidl_runtime_py.utilities import get_message
from rosidl_runtime_py import message_to_ordereddict
from rclpy.qos import qos_profile_sensor_data
import importlib
import time
import rclpy


# ----------------------------------------------------------------------
# Draggable Tree
# ----------------------------------------------------------------------
class DraggableTree(QTreeWidget):
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item or not item.parent():
            return

        # Collect hierarchy from item up to topic root (list of node texts, from top-level field down)
        hierarchy = []
        current = item
        while current is not None:
            parent = current.parent()
            if parent is None:
                topic = current.text(0)
                break
            hierarchy.insert(0, current.text(0))
            current = parent

        # Collapse parent + indexed-child duplicates:
        # e.g. ['data', 'data[0]'] -> ['data[0]']
        final_parts = []
        for p in hierarchy:
            if final_parts and p.startswith(final_parts[-1] + "["):
                # child already encodes parent as indexed element -> replace parent with child
                final_parts[-1] = p
            else:
                final_parts.append(p)

        # Join with dots to form the field path, array entries remain part of the token
        field_path = ".".join(final_parts)

        # Special mapping for /synced_sensors (hub, sensor -> data[index])
        # hierarchy for a synced sensor leaf will be like ['hub_name', 'sensor_name']
        if len(final_parts) == 2 and topic == "/synced_sensors":
            hub, field = final_parts
            field_path = f"data[{synced_sensor_index_map.get((hub, field), -1)}]"

        # DEBUG: uncomment to see exactly what's being dragged
        # print(f"[DEBUG DRAG] {topic}|{field_path}")

        mime_data = QMimeData()
        mime_data.setText(f"{topic}|{field_path}")
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)


# ----------------------------------------------------------------------
# Topic Explorer
# ----------------------------------------------------------------------
class TopicExplorer(QWidget):
    plot_requested = pyqtSignal(str, str, str)

    # Safety cap on how many indexed children to create for one array, so a
    # pathologically large array can never freeze the tree.
    MAX_ARRAY_INDICES = 4096

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.refresh_btn = QPushButton("Refresh Topics")
        self.refresh_btn.clicked.connect(self.refresh_topics)

        self.tree = DraggableTree()
        self.tree.setHeaderLabels(["Topic / Field"])
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree.setDragEnabled(True)
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)

        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.refresh_topics()

    # ------------------------------------------------------------------
    # Refresh and populate topics
    # ------------------------------------------------------------------
    def refresh_topics(self):
        self.tree.clear()
        # One live sample per topic is cached here for this refresh so that real
        # array lengths (e.g. intensities) can be resolved without re-subscribing
        # once per array field.
        self._sample_cache = {}
        topics = get_ros2_topics()

        # Batch-fetch one live sample for every array-bearing topic in a SINGLE
        # shared spin window (instead of subscribing + waiting up to 0.5s per
        # topic sequentially). This cuts refresh time from N x timeout down to
        # roughly one publish interval, so the UI no longer stalls for seconds.
        self._prefetch_samples(topics)

        for topic, type_name in topics:
            parent = QTreeWidgetItem([topic])
            self.tree.addTopLevelItem(parent)

            # Special case for /synced_sensors
            from widgets.ros_helpers import get_topic_fields
            fields = get_topic_fields(type_name, topic)
            if topic == "/synced_sensors" and isinstance(fields, list) and isinstance(fields[0], tuple):
                for hub_name, sensors in fields:
                    hub_item = QTreeWidgetItem([hub_name])
                    parent.addChild(hub_item)
                    for sensor_name in sensors:
                        hub_item.addChild(QTreeWidgetItem([sensor_name]))
                    hub_item.setExpanded(False)
            else:
                # Pull one live sample (once per topic) so real array lengths can
                # be resolved. Only needed when the type actually contains an array
                # and isn't a MultiArray (those still expand via the dedicated
                # _expand_multiarray_data path below).
                sample = None
                if "MultiArray" not in type_name and self._type_has_array(type_name):
                    sample = self._get_topic_sample(type_name, topic)
                # Recursively introspect all fields
                self._add_message_fields(parent, type_name, topic, sample_obj=sample)

            parent.setExpanded(False)

    # ------------------------------------------------------------------
    # Recursive introspection
    # ------------------------------------------------------------------
    def _add_message_fields(self, parent_item, type_name, topic_name, depth=0, max_depth=6, sample_obj=None):
        if depth > max_depth:
            return
        try:
            msg_type = get_message(type_name)
            field_map = getattr(msg_type, "_fields_and_field_types", {})

            for field_name, field_type in field_map.items():
                normalized_type = field_type.replace(" ", "")

                # --- Handle array-like fields ---
                if (
                    normalized_type.startswith("sequence<")
                    or normalized_type.endswith("[]")
                    or "[" in normalized_type and "]" in normalized_type
                ):
                    # extract inner type
                    if normalized_type.startswith("sequence<"):
                        inner_type = normalized_type.split("<")[1].split(",")[0].replace(">", "")
                    else:
                        inner_type = normalized_type.split("[")[0]

                    array_item = QTreeWidgetItem([field_name])
                    parent_item.addChild(array_item)

                    # Expand MultiArray dynamically (unchanged, proven path)
                    if "MultiArray" in type_name and field_name == "data":
                        self._expand_multiarray_data(array_item, type_name, topic_name)
                        continue

                    # Resolve the REAL length from a live sample message if we have
                    # one; otherwise fall back to a few placeholder indices.
                    arr = None
                    length = None
                    if sample_obj is not None:
                        arr = getattr(sample_obj, field_name, None)
                        if arr is not None:
                            try:
                                length = len(arr)
                            except TypeError:
                                length = None

                    is_primitive = inner_type.lower() in (
                        "float", "float32", "float64", "double",
                        "int8", "int16", "int32", "int64",
                        "uint8", "uint16", "uint32", "uint64",
                        "int", "uint", "byte", "char", "bool",
                    )

                    if is_primitive:
                        # Real length when known; else keep the old 3-placeholder
                        # behaviour so a silent topic is no worse than before.
                        count = length if length is not None else 3
                        for i in range(min(count, self.MAX_ARRAY_INDICES)):
                            array_item.addChild(QTreeWidgetItem([f"{field_name}[{i}]"]))
                    else:
                        # Array of sub-messages: expand to real length (only possible
                        # with a live sample) and recurse into each element so deeply
                        # nested values (e.g. poses[2].pose.position.x) are reachable.
                        count = length if length is not None else 0
                        for i in range(min(count, self.MAX_ARRAY_INDICES)):
                            idx_item = QTreeWidgetItem([f"{field_name}[{i}]"])
                            array_item.addChild(idx_item)
                            elem = None
                            try:
                                elem = arr[i] if arr is not None else None
                            except Exception:
                                elem = None
                            self._add_message_fields(
                                idx_item, inner_type, topic_name,
                                depth + 1, max_depth, sample_obj=elem
                            )
                    continue

                # --- Handle sub-message (nested) ---
                if "/" in normalized_type:
                    sub_item = QTreeWidgetItem([field_name])
                    parent_item.addChild(sub_item)
                    sub_sample = getattr(sample_obj, field_name, None) if sample_obj is not None else None
                    self._add_message_fields(
                        sub_item, normalized_type, topic_name,
                        depth + 1, max_depth, sample_obj=sub_sample
                    )
                else:
                    # --- Primitive field ---
                    parent_item.addChild(QTreeWidgetItem([field_name]))

        except Exception as e:
            print(f"[TopicExplorer] Failed to introspect {type_name} ({topic_name}): {e}")


    # ------------------------------------------------------------------
    # Expand MultiArray dynamically (data[0] … data[n-1])
    # ------------------------------------------------------------------
    def _expand_multiarray_data(self, parent_item, type_name, topic_name):
        try:
            msg_type_name = type_name.replace("/", ".")
            module_name, class_name = msg_type_name.rsplit(".", 1)
            module = importlib.import_module(module_name)
            msg_class = getattr(module, class_name)

            from widgets.ros_manager import ROS2Manager
            node = ROS2Manager.instance().node

            received = {"msg": None}

            def cb(msg):
                received["msg"] = msg

            temp_sub = node.create_subscription(msg_class, topic_name, cb, qos_profile_sensor_data)
            start = time.time()
            while rclpy.ok() and received["msg"] is None and (time.time() - start) < 1.0:
                rclpy.spin_once(node, timeout_sec=0.1)
            node.destroy_subscription(temp_sub)

            if received["msg"] and hasattr(received["msg"], "data"):
                data_len = len(received["msg"].data)
                for i in range(data_len):
                    parent_item.addChild(QTreeWidgetItem([f"data[{i}]"]))
                print(f"[INFO] Added {data_len} data indices for {topic_name}")

        except Exception as e:
            print(f"[WARN] Failed to expand MultiArray for {topic_name}: {e}")

    # ------------------------------------------------------------------
    # Does a message type contain any array field anywhere in its tree?
    # ------------------------------------------------------------------
    def _type_has_array(self, type_name, depth=0, max_depth=6, _seen=None):
        if depth > max_depth:
            return False
        if _seen is None:
            _seen = set()
        if type_name in _seen:
            return False
        _seen.add(type_name)
        try:
            msg_type = get_message(type_name)
        except Exception:
            return False
        field_map = getattr(msg_type, "_fields_and_field_types", {})
        for _fname, ftype in field_map.items():
            nt = ftype.replace(" ", "")
            if nt.startswith("sequence<") or nt.endswith("[]") or ("[" in nt and "]" in nt):
                return True
            if "/" in nt and self._type_has_array(nt, depth + 1, max_depth, _seen):
                return True
        return False

    # ------------------------------------------------------------------
    # Grab one live message for a topic (cached per refresh).
    # Returns the message object, or None if nothing arrives in time.
    # ------------------------------------------------------------------
    def _prefetch_samples(self, topics, total_timeout=0.9):
        """Subscribe to every array-bearing topic at once and spin a single
        bounded window, returning as soon as all have produced a sample. Results
        land in self._sample_cache so the per-field code never re-subscribes."""
        cache = getattr(self, "_sample_cache", None)
        if cache is None:
            cache = self._sample_cache = {}
        try:
            from widgets.ros_manager import ROS2Manager
            node = ROS2Manager.instance().node
        except Exception as e:
            print(f"[TopicExplorer] prefetch unavailable: {e}")
            return

        subs = []
        pending = {}
        for topic, type_name in topics:
            if topic in cache:
                continue
            if "MultiArray" in type_name or not self._type_has_array(type_name):
                continue
            try:
                module_name, class_name = type_name.replace("/", ".").rsplit(".", 1)
                msg_class = getattr(importlib.import_module(module_name), class_name)
                holder = {"msg": None}
                sub = node.create_subscription(
                    msg_class, topic,
                    lambda m, h=holder: h.__setitem__("msg", m),
                    qos_profile_sensor_data,
                )
                subs.append(sub)
                pending[topic] = holder
            except Exception as e:
                print(f"[TopicExplorer] subscribe failed for {topic}: {e}")
                cache[topic] = None

        if subs:
            start = time.time()
            while rclpy.ok() and (time.time() - start) < total_timeout:
                if all(h["msg"] is not None for h in pending.values()):
                    break
                rclpy.spin_once(node, timeout_sec=0.02)
            for topic, holder in pending.items():
                cache[topic] = holder["msg"]
            for sub in subs:
                try:
                    node.destroy_subscription(sub)
                except Exception:
                    pass

    def _get_topic_sample(self, type_name, topic_name, timeout=0.5):
        cache = getattr(self, "_sample_cache", None)
        if cache is None:
            cache = self._sample_cache = {}
        if topic_name in cache:
            return cache[topic_name]

        sample = None
        try:
            module_name, class_name = type_name.replace("/", ".").rsplit(".", 1)
            module = importlib.import_module(module_name)
            msg_class = getattr(module, class_name)

            from widgets.ros_manager import ROS2Manager
            node = ROS2Manager.instance().node

            holder = {"msg": None}
            temp_sub = node.create_subscription(
                msg_class, topic_name, lambda m: holder.__setitem__("msg", m),
                qos_profile_sensor_data
            )
            start = time.time()
            while rclpy.ok() and holder["msg"] is None and (time.time() - start) < timeout:
                rclpy.spin_once(node, timeout_sec=0.05)
            node.destroy_subscription(temp_sub)
            sample = holder["msg"]
        except Exception as e:
            print(f"[TopicExplorer] sample fetch failed for {topic_name}: {e}")

        cache[topic_name] = sample
        return sample