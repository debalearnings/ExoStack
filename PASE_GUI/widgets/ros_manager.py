# widgets/ros_manager.py
import rclpy
from rclpy.node import Node
from threading import Lock, Thread, Event
import time

class ROS2Manager:
    _instance = None

    def __init__(self):
        if not rclpy.ok():
            rclpy.init(args=None)
        self.node = Node("ros2_gui_manager")

        self._subscriptions = {}
        self._listeners = {}
        self._msg_cache = {}
        self._lock = Lock()

        # Thread-based spinning
        self._stop_event = Event()
        self._spin_thread = Thread(target=self._spin_loop, daemon=True)
        self._spin_thread.start()

        print("[ROS2Manager] background spin thread started")

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ROS2Manager()
        return cls._instance

    # ------------------ Threaded spin loop ------------------
    def _spin_loop(self):
        while not self._stop_event.is_set():
            try:
                rclpy.spin_once(self.node, timeout_sec=0.01)
            except Exception as e:
                print(f"[ROS2Manager] spin_once error: {e}")
            time.sleep(0.001)  # small sleep to avoid 100% CPU

    # ------------------ Callbacks ------------------
    def _internal_callback(self, topic):
        def _cb(msg):
            with self._lock:
                self._msg_cache[topic] = msg
                listeners = list(self._listeners.get(topic, []))
            # call outside lock
            for cb in listeners:
                try:
                    cb(msg)
                except Exception as e:
                    print(f"[ROS2Manager] listener callback error for {topic}: {e}")
        return _cb

    def ensure_subscription(self, topic, msg_type, qos_profile):
        if topic in self._subscriptions:
            return self._subscriptions[topic]
        try:
            sub = self.node.create_subscription(msg_type, topic, self._internal_callback(topic), qos_profile)
            self._subscriptions[topic] = sub
            print(f"[ROS2Manager] created subscription for {topic}")
            return sub
        except Exception as e:
            print(f"[ROS2Manager] failed to create subscription for {topic}: {e}")
            return None

    def register_listener(self, topic, listener_callable):
        with self._lock:
            self._listeners.setdefault(topic, []).append(listener_callable)
            msg = self._msg_cache.get(topic)
        if msg is not None:
            try:
                listener_callable(msg)
            except Exception:
                pass

    def unregister_listener(self, topic, listener_callable):
        with self._lock:
            if topic in self._listeners and listener_callable in self._listeners[topic]:
                self._listeners[topic].remove(listener_callable)

    def get_last_message(self, topic):
        with self._lock:
            return self._msg_cache.get(topic)

    def shutdown(self):
        print("[ROS2Manager] shutting down...")
        self._stop_event.set()
        try:
            self._spin_thread.join(timeout=2.0)
        except Exception:
            pass
        for sub in list(self._subscriptions.values()):
            try:
                self.node.destroy_subscription(sub)
            except Exception:
                pass
        try:
            self.node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()
        ROS2Manager._instance = None
        print("[ROS2Manager] shutdown complete.")
