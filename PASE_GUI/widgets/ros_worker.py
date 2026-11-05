import rclpy
from rclpy.node import Node
from PyQt5.QtCore import QThread, pyqtSignal


class ROSWorker(QThread):
    topic_list_updated = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.node = None
        self.running = True
        self.subscriptions = {}

    def run(self):
        rclpy.init(args=None)
        self.node = Node("gui_worker")
        while rclpy.ok() and self.running:
            rclpy.spin_once(self.node, timeout_sec=0.1)
        if self.node is not None:
            self.node.destroy_node()
        rclpy.shutdown()

    def request_topic_list(self):
        """Fetch and emit all available topics."""
        if self.node is None:
            return
        try:
            topics = self.node.get_topic_names_and_types()
            topic_list = []

            # ✅ Handle both dict and list return types
            if isinstance(topics, dict):
                topic_list = [(name, types[0]) for name, types in topics.items() if types]
            elif isinstance(topics, list):
                topic_list = [(name, types[0]) for name, types in topics if types]

            self.topic_list_updated.emit(topic_list)

        except Exception as e:
            print(f"[ROSWorker] Failed to fetch topics: {e}")

    def add_subscription(self, topic, msg_type, field_path, callback):
        """Subscribe dynamically to a topic and push data to callback."""
        from rosidl_runtime_py.utilities import get_message
        try:
            msg_class = get_message(msg_type)
        except Exception as e:
            print(f"[ROSWorker] Cannot import message type {msg_type}: {e}")
            return

        def subscriber_cb(msg):
            value = msg
            if field_path:
                for attr in field_path.split('.'):
                    value = getattr(value, attr, None)
                    if value is None:
                        return
            callback(value)

        sub = self.node.create_subscription(msg_class, topic, subscriber_cb, 10)
        self.subscriptions[topic] = sub
        print(f"[ROSWorker] Subscribed to {topic}")

    def shutdown(self):
        self.running = False
