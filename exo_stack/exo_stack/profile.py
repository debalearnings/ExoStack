import os
import sys
import yaml
import importlib
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, Float32
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

class GenericProfileBuilder(Node):
    def __init__(self, profile_name: str):
        
        super().__init__(profile_name)

        # locate config files
        home = os.path.expanduser("~")
        config_path = os.path.join(home, "exo_stack_resources", "config")
        profile_yaml = os.path.join(config_path, "profile.yaml")
        mplanner_yaml = os.path.join(config_path, "mplanner.yaml")

        # load yaml
        with open(profile_yaml, "r") as f:
            profiles_cfg = yaml.safe_load(f)["profiles"]
        with open(mplanner_yaml, "r") as f:
            planners_cfg = yaml.safe_load(f)["planners"]

        if profile_name not in profiles_cfg:
            raise ValueError(f"Profile {profile_name} not found in profile.yaml")

        self.profile_cfg = profiles_cfg[profile_name]

        # find matching planner entry in mplanner.yaml
        planner_name = self.profile_cfg["planner_name"]
        if planner_name not in planners_cfg:
            raise ValueError(f"Planner {planner_name} not in mplanner.yaml")
        self.planner_cfg = planners_cfg[planner_name]

        # load builder algo class dynamically
        self.builder_algo = self.profile_cfg["profile_builder_algo"]
        self.profile_type = "List" if self.builder_algo.endswith("List") else "Function"
 
        algo_path = os.path.expanduser(f'~/exo_stack_resources/algo/builder/{self.builder_algo}.py')
        spec_algo = importlib.util.spec_from_file_location(self.builder_algo, algo_path)
        algo_module = importlib.util.module_from_spec(spec_algo)
        spec_algo.loader.exec_module(algo_module)
        BuilderClass = getattr(algo_module, self.builder_algo)

        self.builder = BuilderClass()

        # sanity check type
        if not self.planner_cfg["profile_type"].endswith(self.profile_type):
            self.get_logger().warn(
                f"MISMATCH: planner requires {self.planner_cfg['profile_type']} "
                f"but builder is {self.profile_type}"
            )
            self.valid = False
        else:
            self.valid = True

         # QoS profile for best effort
        qos_best_effort = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)

        # publisher
        self.profile_pub = self.create_publisher(
            Float32MultiArray, self.planner_cfg["profile_topic"], qos_profile=qos_best_effort
        )

        # Mode-specific setup
        self.mode = self.profile_cfg["mode"]
        if self.mode == "HIL":
            hil_topic = self.profile_cfg["hil_output_topic"]
            self.create_subscription(Float32MultiArray, hil_topic, self.hil_callback, qos_profile=qos_best_effort)
        elif self.mode == "Deployment":
            self.speed = None
            self.intent = None
            if self.profile_cfg.get("speed_required"):
                self.create_subscription(Float32, 
                                         self.profile_cfg["speed_topic"], 
                                         self.speed_callback, 
                                         qos_profile=qos_best_effort)
            if self.profile_cfg.get("intent_required"):
                self.create_subscription(Float32, 
                                         self.profile_cfg["intent_topic"], 
                                         self.intent_callback, 
                                         qos_profile=qos_best_effort)
            rate = self.profile_cfg.get("rate", 50)
            self.timer = self.create_timer(1.0/rate, self.deployment_timer_cb)

            # load lookup algo if given
            self.lookup_algo = self.profile_cfg.get("lookup_algo")
            if self.lookup_algo:

                algo_path = os.path.expanduser(f'~/exo_stack_resources/algo/lookup_algo/{self.lookup_algo}.py')
                spec_algo = importlib.util.spec_from_file_location(self.lookup_algo, algo_path)
                algo_module = importlib.util.module_from_spec(spec_algo)
                spec_algo.loader.exec_module(algo_module)
                LookupAlgoClass = getattr(algo_module, self.lookup_algo)    

                
                lookup_name = self.profile_cfg["lookup_table"]
                if not lookup_name.endswith(".json"):
                    lookup_name += ".json"

                json_path = os.path.join(
                    home,
                    "exo_stack_resources",
                    "lookup_table",
                    lookup_name
                )

                # json_path = os.path.join(home, "exo_stack_resources", "lookup_table", self.profile_cfg["lookup_table"])
                self.lookup = LookupAlgoClass(json_path)

    # Callbacks
    def hil_callback(self, msg):
        if not self.valid: return
        data = list(msg.data)
        profile_number=data[0]
        values = data[1:]

        try:
            prof = self.builder.buildprofile(values)
        except ValueError as e:
            self.get_logger().error(f"Builder rejected input: {e}. Got values={values}")
            return

        # prepend the profile number
        prof = [float(profile_number)] + prof  

        
        prof.append(0.0)  # emergency stop = 0 by default

        self.publish_profile(prof)

    def speed_callback(self, msg):
        self.speed = msg.data

    def intent_callback(self, msg):
        self.intent = msg.data

    def deployment_timer_cb(self):
        if not self.valid: return
        if self.speed is None or (self.profile_cfg.get("intent_required") and self.intent is None):
            return

        args = []
        if self.profile_cfg.get("speed_required"):
            args.append(self.speed)
        if self.profile_cfg.get("intent_required"):
            args.append(self.intent)

        lookup_values = self.lookup.readlookuptable(args) if hasattr(self, "lookup") else []
        prof = self.builder.buildprofile(lookup_values)

        # emergency stop: intent == 0 means stop
        stop_flag = 1.0 if self.intent == 0 else 0.0
        prof.append(stop_flag)

        prof.insert(0, 0.0) #dummy profile number

        self.publish_profile(prof)

    def publish_profile(self, prof_list):
        msg = Float32MultiArray()
        msg.data = prof_list
        self.profile_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    # take profile_name from argv[1]
    if len(sys.argv) < 2:
        raise ValueError("No profile name specified")
    profile_name = sys.argv[1]
    node = GenericProfileBuilder(profile_name)
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
