#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32MultiArray, Int32
from message_filters import Subscriber, ApproximateTimeSynchronizer
import yaml
import os
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from ament_index_python.packages import get_package_share_directory
import time


class GenericSyncNode(Node):
    def __init__(self):
        super().__init__('generic_sync_node')

        # -------------------------------
        # Config file resolution
        # -------------------------------
        # Declare ROS2 parameter
        self.declare_parameter('config_path', '')

        # 1. Parameter takes highest priority
        config_path = self.get_parameter('config_path').get_parameter_value().string_value

        # 2. If no parameter, check environment variable
        if not config_path:
            config_path = os.path.expanduser("~/exo_stack_resources/config/sensors.yaml")

        # 3. Otherwise fallback to installed share folder
        if not config_path:
            package_share_dir = get_package_share_directory('package1')  # change package name
            config_path = os.path.join(package_share_dir, 'config', 'sensors.yaml')

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        self.get_logger().info(f"Using config file: {config_path}")

        # Load YAML config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.hubs = config.get('hubs', {}) 
        self.slop_time = config.get('slop_time', 0.01)
        self.output_topic = config.get('output_topic', '/synced_sensors')

        self.get_logger().info(f"Using slop_time: {self.slop_time}")
        self.get_logger().info(f"Publishing concatenated data to: {self.output_topic}")

        # -------------------------------
        # QoS and Subscribers
        # -------------------------------
        best_effort_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=10
        )

        qos2 = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=10
        )

        self.subscribers = []
        self.hub_keys = []
        for hub_key, hub_info in self.hubs.items():
            topic = hub_info['topic']
            self.get_logger().info(f"Subscribing to topic {topic} for hub {hub_key}")
            self.subscribers.append(Subscriber(self, LaserScan, topic, qos_profile=best_effort_qos))
            # self.subscribers.append(Subscriber(self, LaserScan, topic, qos_profile=qos2))
            self.hub_keys.append(hub_key)

        # Synchronizer
        self.ts = None
        self.reset_synchronizer()

        # Publisher with Best Effort QoS
        self.publisher = self.create_publisher(Float32MultiArray, self.output_topic, best_effort_qos)

        # Trigger publisher (to ESP32s)
        self.trigger_pub = self.create_publisher(Int32, '/sync_trigger', best_effort_qos)

        # State variables
        self.sync_active = False
        self.last_sync_time = time.time()
        self.trigger_mode = True   # Start in trigger mode
        self.trigger_msg = Int32()
        self.trigger_msg.data = 0

        # Timers
        self.trigger_timer = self.create_timer(0.2, self.trigger_loop)  # 5 Hz
        self.monitor_timer = self.create_timer(1.0, self.monitor_sync)

        # Index mapping (optional)
        index = 0
        self.index_map = {}
        for hub_key in self.hub_keys:
            for sensor_name in self.hubs[hub_key]['sensors']:
                self.index_map[index] = f"{hub_key}.{sensor_name}"
                index += 1
        self.get_logger().info(f"Index mapping: {self.index_map}")


        self.last_processed_timestamps=[0.0, 0.0]


    # -------------------------------
    # Core functions
    # -------------------------------
    def reset_synchronizer(self):
        """Recreate the ApproximateTimeSynchronizer to clear old buffers."""
        if self.ts is not None:
            self.get_logger().info("Destroying old synchronizer")
            self.ts = None

        self.ts = ApproximateTimeSynchronizer(
            self.subscribers, queue_size=5, slop=self.slop_time
        )
        self.ts.registerCallback(self.sync_callback)
        self.get_logger().info("New synchronizer created")

    def trigger_loop(self):
        """Periodically send sync triggers when in trigger mode."""
        if self.trigger_mode:
            self.trigger_pub.publish(self.trigger_msg)
            self.get_logger().debug("Sent sync trigger (Best Effort)")
            self.reset_synchronizer()

    def monitor_sync(self):
        """Check if sync is healthy; if not, retrigger."""
        now = time.time()
        if self.sync_active and (now - self.last_sync_time > 1.0):
            self.get_logger().warn("No synced messages for >1s, entering TRIGGER mode")
            self.trigger_mode = True
            self.sync_active = False
            self.reset_synchronizer()

    def sync_callback(self, *msgs):

        # Get timestamps
        timestamps = [msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9 for msg in msgs]

        # Prevent duplicate matches (same timestamps as last callback)
        if self.last_processed_timestamps == timestamps:
            return
        self.last_processed_timestamps = timestamps

        """Callback when synchronized messages arrive."""
        concatenated = []
        timestamps = []

        for hub_key, msg in zip(self.hub_keys, msgs):
            hub_sensors = self.hubs[hub_key]['sensors']
            intensities = list(msg.intensities)
            if len(intensities) < len(hub_sensors):
                self.get_logger().warn(
                    f"{hub_key}: Expected {len(hub_sensors)} intensities, got {len(intensities)}"
                )

            # self.get_logger().info(f"MATCH {intensities[0]}")
            concatenated.extend(intensities[:len(hub_sensors)])

            t_sec = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            timestamps.append(t_sec)

        for i in range(len(timestamps)-1):
            dt = abs(timestamps[i+1] - timestamps[i])
            # self.get_logger().info(
            #     f"Time difference {self.hub_keys[i]} vs {self.hub_keys[i+1]}: {dt:.6f} s"
            # )

        out_msg = Float32MultiArray()
        out_msg.data = concatenated
        self.publisher.publish(out_msg)


        self.last_sync_time = time.time()
        if self.trigger_mode:
            self.get_logger().info("Synchronized messages detected → SYNC MODE")
            self.trigger_mode = False
            self.sync_active = True


def main(args=None):
    rclpy.init(args=args)
    node = GenericSyncNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Node stopped by user.")
    finally:
        node.destroy_node()
        if rclpy.ok():  # Check if the context is still active
            rclpy.shutdown() 


if __name__ == '__main__':
    main()
