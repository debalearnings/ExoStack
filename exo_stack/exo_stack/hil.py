#!/usr/bin/env python3
import os
import sys
import yaml
import importlib
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
import csv
from datetime import datetime


class GenericHILNode(Node):
    def __init__(self, profile_name: str):
        super().__init__(profile_name)

        # ----------------------
        # Load profile.yaml
        # ----------------------
        home = os.path.expanduser("~")
        config_path = os.path.join(home, "exo_stack_resources", "config")
        profile_yaml = os.path.join(config_path, "profile.yaml")

        with open(profile_yaml, "r") as f:
            profiles_cfg = yaml.safe_load(f)["profiles"]

        if profile_name not in profiles_cfg:
            raise ValueError(f"Profile {profile_name} not found in profile.yaml")
        self.profile_cfg = profiles_cfg[profile_name]

        # ----------------------
        # QoS for best effort
        # ----------------------
        qos = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)

        # ----------------------
        # Publisher for candidates
        # ----------------------
        self.hil_output_topic = self.profile_cfg["hil_output_topic"]
        self.profile_pub = self.create_publisher(Float32MultiArray, self.hil_output_topic, qos)

        # ----------------------
        # Subscriber for cost feedback
        # ----------------------
        self.hil_cost_topic = self.profile_cfg["cost_topic"]
        self.create_subscription(Float32MultiArray, self.hil_cost_topic, self.cost_callback, qos)

        # ----------------------
        # Initialize optimizer dynamically
        # ----------------------
        hil_algo_name = self.profile_cfg["hil_algo"].upper()  # e.g. "CMA_ES" or "BAYESIAN"
        algo_path = os.path.expanduser(f'~/exo_stack_resources/algo/hil_optimizer/{hil_algo_name}.py')
        spec_algo = importlib.util.spec_from_file_location(f"{hil_algo_name}", algo_path)
        algo_module = importlib.util.module_from_spec(spec_algo)
        spec_algo.loader.exec_module(algo_module)

        # Class name = OPT_<ALGO>
        OptimizerClass = getattr(algo_module, f"{hil_algo_name}")

        hyperparams = self.profile_cfg.get("hil_hyperparams", {})
        self.optimizer = OptimizerClass(**hyperparams)

        # ----------------------
        # Initialize state
        # ----------------------
        self.profile_number = 0
        self.current_candidate = None
        self.waiting_for_cost = False

        # NEW: Store results + algo info
        self.results = []
        self.algo_name = hil_algo_name
        self.cost_algo = self.profile_cfg.get("cost_algo", "unknown")
        self.cost_params = self.profile_cfg.get("cost_params", [])

        # Start loop
        self.create_timer(0.01, self.publish_next_candidate)

    # ----------------------
    # Candidate publication
    # ----------------------
    def publish_next_candidate(self):
        if self.waiting_for_cost:
            return

        # NEW: stop condition
        if hasattr(self.optimizer, "is_done") and self.optimizer.is_done():
            best_point, best_score = self.optimizer.get_best_so_far()
            self.get_logger().info(f"Optimization finished. Best candidate: {best_point}, Score: {best_score}")
            self.save_results(best_point, best_score)
            rclpy.shutdown()
            return

        candidate = self.optimizer.get_next_candidate()  # list of floats
        self.profile_number += 1
        self.current_candidate = candidate

        msg = Float32MultiArray()
        msg.data = [float(self.profile_number)] + [float(x) for x in candidate]
        self.profile_pub.publish(msg)

        self.waiting_for_cost = True
        self.get_logger().info(f"Published candidate #{self.profile_number}: {candidate}")

    # ----------------------
    # Cost feedback callback
    # ----------------------
    def cost_callback(self, msg: Float32MultiArray):
        if not self.waiting_for_cost:
            return

        data = list(msg.data)
        recv_profile_number = int(data[0])
        cost = float(data[1])

        if recv_profile_number != self.profile_number:
            self.get_logger().warn(
                f"Profile number mismatch: expected {self.profile_number}, got {recv_profile_number}. Ignoring."
            )
            return

        # NEW: store candidate + cost
        self.results.append([recv_profile_number] + self.current_candidate + [cost])

        self.optimizer.submit_result(self.current_candidate, cost)
        self.waiting_for_cost = False
        self.get_logger().info(f"Received cost {cost:.3f} for profile #{recv_profile_number}")

    # ----------------------
    # Save results to CSV
    # ----------------------
    def save_results(self, best_point, best_score):
        home = os.path.expanduser("~")
        results_dir = os.path.join(home, "exo_stack_resources", "hil_results")
        os.makedirs(results_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        params_str = "_".join(str(x) for x in self.cost_params)
        fname = f"HIL_{self.algo_name}_{self.cost_algo}_{params_str}_{timestamp}.csv"
        filepath = os.path.join(results_dir, fname)

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            # header
            writer.writerow(["profile_number"] +
                            [f"param_{i+1}" for i in range(len(best_point) if best_point else 0)] +
                            ["cost"])
            # all results
            writer.writerows(self.results)
            # best result
            if best_point is not None:
                writer.writerow(["BEST"] + best_point + [best_score])

        self.get_logger().info(f"Results saved to {filepath}")


def main(args=None):
    rclpy.init(args=args)

    if len(sys.argv) < 2:
        raise ValueError("Profile name must be provided as argument")
    profile_name = sys.argv[1]

    node = GenericHILNode(profile_name)

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
