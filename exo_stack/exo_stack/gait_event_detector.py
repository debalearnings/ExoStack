import os
import sys
import yaml
import importlib.util

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, Float32MultiArray
from rclpy.qos import QoSProfile, QoSReliabilityPolicy


class EventDetectorNode(Node):
    def __init__(self, event_key: str):
        
        # Node name is the event_key
        super().__init__(event_key)

        # --- Load config file (always gait_events.yaml) ---
        config_path = os.path.expanduser('~/exo_stack_resources/config/gait_events.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

       
        if "events" not in config:
            raise RuntimeError("Config file missing 'events' section.")

        events_cfg = config['events']

        if event_key not in events_cfg:
            raise RuntimeError(f"Event key '{event_key}' not found under 'events' in config file.")

        event_cfg = events_cfg[event_key]


        # --- Extract details ---
        self.input_topic = event_cfg['input_topic']
        self.output_topic = event_cfg['output_topic']
        self.sensors = event_cfg['sensors']
        self.parameterslist = event_cfg.get('parameters', [])
        self.history_size = event_cfg.get('history_size', 1)
        self.algorithm = event_cfg['algorithm']

        # --- Import SensorUtil ---
        sensor_util_path = os.path.expanduser('~/exo_stack_resources/util/SensorUtil.py')
        spec_sensor = importlib.util.spec_from_file_location("SensorUtil", sensor_util_path)
        sensor_module = importlib.util.module_from_spec(spec_sensor)
        spec_sensor.loader.exec_module(sensor_module)
        SensorUtil = getattr(sensor_module, "SensorUtil")

        # --- Import Algorithm class dynamically ---
        algo_path = os.path.expanduser(f'~/exo_stack_resources/algo/gait_events/{self.algorithm}.py')
        spec_algo = importlib.util.spec_from_file_location(self.algorithm, algo_path)
        algo_module = importlib.util.module_from_spec(spec_algo)
        spec_algo.loader.exec_module(algo_module)
        DetectorClass = getattr(algo_module, self.algorithm)

        # --- Init utilities ---
        self.sensor_util = SensorUtil(None, self.sensors)
        self.detector = DetectorClass(self.history_size, self.parameterslist)

        # --- ROS pub/sub (Best Effort QoS) ---
        qos_profile = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT, depth=10)
        self.publisher = self.create_publisher(Int32, self.output_topic, qos_profile)
        # self.publisher = self.create_publisher(Int32, self.output_topic, 10)
        self.subscription = self.create_subscription(
            Float32MultiArray,
            self.input_topic,
            self.listener_callback,
            qos_profile
        )

        
        self.get_logger().info(f"Event detector node '{event_key}' initialized.")

    def listener_callback(self, msg):
        # Convert msg to list of floats
        values = list(msg.data)

        # Get required sensor values
        sensor_values = self.sensor_util.get_sensor_value(values)

        # Run detection
        event = self.detector.detect(sensor_values)

        if event == 1:
            out_msg = Int32()
            out_msg.data = 1
            self.publisher.publish(out_msg)
            self.get_logger().info("Event detected and published.")
        # else:
        #     out_msg = Int32()
        #     out_msg.data = 0
        #     self.publisher.publish(out_msg)


def main(args=None):
    rclpy.init(args=args)

    # --- Get event key from sys.argv[1] (launch file passes this) ---
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        raise RuntimeError(
        "Missing required argument: <event_key>\n"
        "Example: ros2 run <pkg> gait_event_detector.py right_heel_strike"
         )
    event_key = sys.argv[1]

    node = EventDetectorNode(event_key)

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
