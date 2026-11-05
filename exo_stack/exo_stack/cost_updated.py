#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float32MultiArray, Float32, Int32
import numpy as np
import importlib.util
import os
import yaml
import threading


class GenericCostNode(Node):
    def __init__(self, profile_name: str):
        super().__init__(profile_name + "_cost")

        # --- Load profile.yaml ---
        home = os.path.expanduser("~")
        profile_yaml = os.path.join(home, "exo_stack_resources", "config", "profile.yaml")
        with open(profile_yaml, "r") as f:
            profiles_cfg = yaml.safe_load(f)["profiles"]

        if profile_name not in profiles_cfg:
            raise ValueError(f"Profile {profile_name} not found in profile.yaml")
        self.cfg = profiles_cfg[profile_name]

        # --- Config ---
        self.planner_name = self.cfg["planner_name"]
        self.cost_topic = self.cfg["cost_topic"]
        self.cost_algo_name = self.cfg["cost_algo"]
        self.cost_params = self.cfg.get("cost_params", [])
        self.sensors = self.cfg.get("sensors", [])
        self.mode = self.cfg.get("mode", "HIL")  # <-- Added
        self.gait_cycles_to_skip = self.cfg.get("gait_cycles_to_skip", 0)
        self.gait_cycles_to_consider = self.cfg.get("gait_cycles_to_consider", 1)

        # --- Optional gait marker ---
        self.additional_gait_marker_topic = self.cfg.get("additional_gait_marker_topic", None)
        self.gait_marker_value = 0.0

        # --- External sensor topic if sensors list empty ---
        self.external_sensors_topic = self.cfg.get("external_sensors_topic", None)

        # --- Import SensorUtil dynamically only if sensors provided ---
        self.sensor_util = None
        if self.sensors:
            sensor_util_path = os.path.expanduser('~/exo_stack_resources/util/SensorUtil.py')
            spec_sensor = importlib.util.spec_from_file_location("SensorUtil", sensor_util_path)
            sensor_module = importlib.util.module_from_spec(spec_sensor)
            spec_sensor.loader.exec_module(sensor_module)
            SensorUtil = getattr(sensor_module, "SensorUtil")
            self.sensor_util = SensorUtil(hub_sensor_list=self.sensors)

        # --- Algo ---
        algo_path = os.path.expanduser(f'~/exo_stack_resources/algo/cost/{self.cost_algo_name}.py')
        spec_algo = importlib.util.spec_from_file_location(self.cost_algo_name, algo_path)
        algo_module = importlib.util.module_from_spec(spec_algo)
        spec_algo.loader.exec_module(algo_module)
        AlgoClass = getattr(algo_module, self.cost_algo_name)
        self.algo = AlgoClass(*self.cost_params)

        # --- QoS ---
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=10)

        # --- Subscriptions ---
        self.sub_status = self.create_subscription(
            Float32MultiArray,
            f"/{self.planner_name}/profile_status",
            self.status_callback,
            qos,
        )

        if self.sensors:
            self.sub_sensors = self.create_subscription(
                Float32MultiArray,
                "/synced_sensors",
                self.sensors_callback,
                qos,
            )
            self.get_logger().info("Subscribed to /synced_sensors using SensorUtil")
        
        if self.external_sensors_topic:
            self.sub_ext_sensors = self.create_subscription(
                Float32MultiArray,
                self.external_sensors_topic,
                self.external_sensors_callback,
                qos,
            )
            self.get_logger().info(f"Subscribed to external sensors: {self.external_sensors_topic}")
        if not self.sensors and not self.external_sensors_topic:
            self.get_logger().warn("No sensors configured (neither internal nor external)!")

        if self.additional_gait_marker_topic:
            self.sub_gait_marker = self.create_subscription(
                Int32,
                self.additional_gait_marker_topic,
                self.gait_marker_callback,
                qos,
            )
            self.get_logger().info(f"Subscribed to additional gait marker: {self.additional_gait_marker_topic}")

        self.pub_cost = self.create_publisher(Float32MultiArray, self.cost_topic, qos)

        # --- State ---
        self.current_profile = None
        self.current_cycle = None
        self.buffered_data_internal = []
        self.buffered_data_external = []
        self.costs = []
        self.lock = threading.Lock()

        # For deployment mode cycle management
        self.deploy_cycle_counter = 0

        self.get_logger().info(f"GenericCostNode for {profile_name} started in {self.mode} mode.")

    # ----------------------------
    # Callbacks
    # ----------------------------
    def status_callback(self, msg: Float32MultiArray):
        values = msg.data
        if len(values) < 2:
            return

        profile_num = int(values[0])
        cycle_num = int(values[1])
        finalized_cycle = cycle_num - 1

        if self.mode == "Deployment":
            # In deployment mode, profile_num and cycle_num will stay 0
            if self.buffered_data_internal:
                data_to_compute = self.buffered_data_internal.copy()
                self.buffered_data_internal = []
                threading.Thread(
                    target=self._finalize_cycle_deployment,
                    args=(data_to_compute,)
                ).start()

            if self.buffered_data_external:
                data_to_compute_ext = self.buffered_data_external.copy()
                self.buffered_data_external = []
                threading.Thread(
                    target=self._finalize_cycle_deployment,
                    args=(data_to_compute_ext,)
                ).start()

        else:
            # --- Original HIL logic ---
            if profile_num == 0 and cycle_num == 0:
                if self.buffered_data_internal:
                    data_to_compute = self.buffered_data_internal.copy()
                    self.buffered_data_internal = []
                    threading.Thread(
                        target=self._finalize_cycle,
                        args=(self.current_cycle if self.current_cycle is not None else 0, data_to_compute)
                    ).start()

                if self.buffered_data_external:
                    data_to_compute_ext = self.buffered_data_external.copy()
                    self.buffered_data_external = []
                    threading.Thread(
                        target=self._finalize_cycle,
                        args=(self.current_cycle if self.current_cycle is not None else 0, data_to_compute_ext)
                    ).start()
            else:
                if finalized_cycle >= 0:
                    if self.buffered_data_internal:
                        data_to_compute = self.buffered_data_internal.copy()
                        self.buffered_data_internal = []
                        threading.Thread(
                            target=self._finalize_cycle,
                            args=(finalized_cycle, data_to_compute)
                        ).start()

                    if self.buffered_data_external:
                        data_to_compute_ext = self.buffered_data_external.copy()
                        self.buffered_data_external = []
                        threading.Thread(
                            target=self._finalize_cycle,
                            args=(finalized_cycle, data_to_compute_ext)
                        ).start()

            if profile_num != self.current_profile:
                self._reset_profile(profile_num, cycle_num)

            self.current_cycle = cycle_num

    def sensors_callback(self, msg: Float32MultiArray):
        if not self.sensors or not self.sensor_util:
            return
        try:
            row = self.sensor_util.get_sensor_value(msg.data)
            if self.additional_gait_marker_topic:
                row = np.append(row, self.gait_marker_value)
                self.gait_marker_value = 0.0  # consume and reset
            self.buffered_data_internal.append(row)
        except Exception as e:
            self.get_logger().warn(f"Sensor extraction failed: {e}")

    def external_sensors_callback(self, msg: Float32MultiArray):
        row = np.array(msg.data)
        if self.additional_gait_marker_topic:
            row = np.append(row, self.gait_marker_value)
            self.gait_marker_value = 0.0  # consume and reset
        self.buffered_data_external.append(row)

    def gait_marker_callback(self, msg: Int32):
        self.gait_marker_value = float(msg.data)
        # self.get_logger().info(f"Gait marker received: {self.gait_marker_value}")

    # ----------------------------
    # Helpers
    # ----------------------------
    def _reset_profile(self, profile_num: int, cycle_num: int):
        self.current_profile = profile_num
        self.current_cycle = cycle_num
        with self.lock:
            self.costs = []
        self.buffered_data_internal = []
        self.buffered_data_external = []
        self.deploy_cycle_counter = 0
        self.get_logger().info(f"Switched to new profile {profile_num}, starting at cycle {cycle_num}")

    def _finalize_cycle(self, cycle_num: int, data_array):
        if not data_array:
            return
        data_array_np = np.array(data_array)
        cost = self.algo.compute(data_array_np)

        if cycle_num <= self.gait_cycles_to_skip:
            self.get_logger().info(f"Skipped cycle {cycle_num}, cost={cost:.3f}")
        elif cycle_num <= self.gait_cycles_to_skip + self.gait_cycles_to_consider:
            obs_index = cycle_num - self.gait_cycles_to_skip
            with self.lock:
                self.costs.append(cost)
                observed_count = len(self.costs)

            self.get_logger().info(f"Observed cycle {obs_index}, cost={cost:.3f}")

            if observed_count == self.gait_cycles_to_consider:
                avg_cost = float(np.mean(self.costs))
                msg = Float32MultiArray()
                msg.data = [float(self.current_profile), avg_cost]
                self.pub_cost.publish(msg)
                self.get_logger().info(f"Published avg cost {avg_cost:.3f} for profile {self.current_profile}")
        else:
            self.get_logger().info(f"Extra cycle, cost={cost:.3f}")

    def _finalize_cycle_deployment(self, data_array):
        """Handles repeated cycle cost averaging in Deployment mode."""
        if not data_array:
            return
        data_array_np = np.array(data_array)
        cost = self.algo.compute(data_array_np)

        with self.lock:
            self.deploy_cycle_counter += 1

            # Skip initial cycles
            if self.deploy_cycle_counter <= self.gait_cycles_to_skip:
                self.get_logger().info(f"Skipped cycle {self.deploy_cycle_counter}, cost={cost:.3f}")
                return

            # Collect cycles to average
            self.costs.append(cost)
            if len(self.costs) == self.gait_cycles_to_consider:
                avg_cost = float(np.mean(self.costs))
                msg = Float32MultiArray()
                msg.data = [0.0, avg_cost]  # profile=0 for deployment
                self.pub_cost.publish(msg)
                self.get_logger().info(
                    f"Published avg cost {avg_cost:.3f} (Deployment mode, cycles {self.deploy_cycle_counter - self.gait_cycles_to_consider + 1} to {self.deploy_cycle_counter})"
                )
                self.costs = []  # Reset after publishing

            # Reset after completing skip + consider cycles pattern
            total_window = self.gait_cycles_to_skip + self.gait_cycles_to_consider
            if self.deploy_cycle_counter >= total_window:
                self.deploy_cycle_counter = 0


def main(args=None):
    rclpy.init(args=args)
    import sys
    if len(sys.argv) < 2:
        raise RuntimeError("No planner key specified")
    profile_name = sys.argv[1]
    node = GenericCostNode(profile_name)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Node stopped by user.")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()
