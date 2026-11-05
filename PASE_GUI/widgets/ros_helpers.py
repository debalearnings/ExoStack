import importlib
import os
import yaml
import time
import rclpy
from rosidl_runtime_py.utilities import get_message
from rosidl_runtime_py import message_to_ordereddict
from widgets.ros_manager import ROS2Manager
from rclpy.qos import (
    QoSProfile,
    qos_profile_sensor_data,
    ReliabilityPolicy,
    DurabilityPolicy,
    HistoryPolicy,
)

# Global lookup for /synced_sensors mapping
synced_sensor_index_map = {}

# ---------------------------------------------------------------------
# Topic and Message Utilities
# ---------------------------------------------------------------------

def get_ros2_topics():
    manager = ROS2Manager.instance()
    node = manager.node
    topic_list = node.get_topic_names_and_types()
    return [(t, types[0]) for t, types in topic_list]


def _load_synced_sensors_config():
    """
    Parse ~/exo_stack_resources/config/sensors.yaml
    Returns a dict {hub_name: [sensor1, sensor2, ...]} and builds index map.
    """
    global synced_sensor_index_map
    synced_sensor_index_map.clear()

    config_path = os.path.expanduser("~/exo_stack_resources/config/sensors.yaml")
    if not os.path.exists(config_path):
        print(f"[WARN] sensors.yaml not found at {config_path}")
        return {}

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        hubs = data.get("hubs", {})
    except Exception as e:
        print(f"[ERROR] Failed to parse sensors.yaml: {e}")
        return {}

    all_hubs = {}
    idx = 0
    for hub_name, hub_data in hubs.items():
        sensors = hub_data.get("sensors", [])
        all_hubs[hub_name] = sensors
        for sensor in sensors:
            synced_sensor_index_map[(hub_name, sensor)] = idx
            idx += 1
    print(f"[INFO] Parsed {len(synced_sensor_index_map)} synced sensor indices from YAML.")
    return all_hubs


def get_topic_fields(type_name, topic_name=None, max_wait_time=1.0):
    """
    Return field names for a topic. Special case for /synced_sensors (Float32MultiArray).
    """
    if topic_name == "/synced_sensors":
        hubs = _load_synced_sensors_config()
        fields = []
        for hub_name, sensors in hubs.items():
            fields.append((hub_name, sensors))
        return fields  # structured hub -> [sensors]

    # ---------- Normal case ----------
    msg_type = get_message(type_name)
    dummy = msg_type()
    fields = list(message_to_ordereddict(dummy).keys())

    # Handle MultiArray types dynamically
    if 'MultiArray' in type_name and topic_name:
        manager = ROS2Manager.instance()
        node = manager.node
        data_indices = []
        try:
            msg_type_name = type_name.replace('/', '.')
            module_name, class_name = msg_type_name.rsplit('.', 1)
            module = importlib.import_module(module_name)
            msg_class = getattr(module, class_name)
        except Exception as e:
            print(f"[ERROR] Could not load message type {type_name}: {e}")
            return fields

        received = {'msg': None}

        def temp_callback(msg):
            received['msg'] = msg

        temp_sub = node.create_subscription(msg_class, topic_name, temp_callback, qos_profile_sensor_data)
        start = time.time()
        while rclpy.ok() and received['msg'] is None and (time.time() - start) < max_wait_time:
            rclpy.spin_once(node, timeout_sec=0.1)
        node.destroy_subscription(temp_sub)

        if received['msg'] is not None and hasattr(received['msg'], 'data'):
            data_len = len(received['msg'].data)
            data_indices = [f"data[{i}]" for i in range(data_len)]
        if 'data' in fields:
            fields.remove('data')
        fields.extend(data_indices)

    return fields


# ---------------------------------------------------------------------
# QoS Detection and Subscription
# ---------------------------------------------------------------------

def detect_publisher_qos(node, topic_name):
    try:
        info_list = node.get_publishers_info_by_topic(topic_name)
        if not info_list:
            return qos_profile_sensor_data

        pub_info = info_list[0]
        qos_raw = pub_info.qos_profile
        qos_profile = QoSProfile(
            history=getattr(qos_raw, "history", HistoryPolicy.KEEP_LAST),
            depth=getattr(qos_raw, "depth", 10),
            reliability=getattr(qos_raw, "reliability", ReliabilityPolicy.BEST_EFFORT),
            durability=getattr(qos_raw, "durability", DurabilityPolicy.VOLATILE),
        )
        return qos_profile
    except Exception as e:
        print(f"[WARN] QoS detect failed for {topic_name}: {e}")
        return qos_profile_sensor_data


def create_ros_subscriber(topic_name, msg_type_name, callback):
    manager = ROS2Manager.instance()
    node = manager.node
    try:
        msg_type_name = msg_type_name.replace('/', '.')
        module_name, class_name = msg_type_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        msg_type = getattr(module, class_name)
    except Exception as e:
        print(f"[ERROR] Could not load message type {msg_type_name}: {e}")
        return None

    qos_profile = detect_publisher_qos(node, topic_name)
    try:
        return node.create_subscription(msg_type, topic_name, callback, qos_profile)
    except Exception:
        return node.create_subscription(msg_type, topic_name, callback, qos_profile_sensor_data)


# ---------------------------------------------------------------------
# Synced Sensors Mapping Helper
# ---------------------------------------------------------------------

def get_sensor_mapping():
    """
    Returns a list of (hub_name, sensor_name) tuples
    in the same order as they appear in the synced sensor MultiArray.
    Uses cached map if already loaded.
    """
    global synced_sensor_index_map

    # if not already loaded, load it
    if not synced_sensor_index_map:
        _load_synced_sensors_config()

    # Sort by index to preserve proper order
    sorted_items = sorted(synced_sensor_index_map.items(), key=lambda x: x[1])
    mapping = [pair for pair, _ in sorted_items]
    return mapping