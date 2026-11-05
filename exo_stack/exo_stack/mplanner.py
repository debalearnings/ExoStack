import os
import sys
import yaml
import importlib.util
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, Float32MultiArray, Float32
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

class GenericPlannerNode(Node):
    def __init__(self, planner_key: str):
        super().__init__(planner_key)
        
        # --- Manual mode ---
        self.manual_mode_active = False
        self.manual_command_val = 0.0

        # --- Load planner YAML ---
        yaml_path = os.path.expanduser('~/exo_stack_resources/config/mplanner.yaml')
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'planners' not in config or planner_key not in config['planners']:
            raise RuntimeError(f"Planner key '{planner_key}' not found in YAML.")
        
        planner_cfg = config['planners'][planner_key]

        # --- Extract planner details ---
        self.gait_event_topic = planner_cfg['gait_event_topic']
        self.planner_algorithm_name = planner_cfg['planner_algorithm']
        self.profile_topic = planner_cfg['profile_topic']
        self.output_topic = planner_cfg['output_topic']
        self.profile_type = planner_cfg['profile_type']
        self.approach = planner_cfg['approach']
        self.gait_phase_topic = planner_cfg.get('gait_phase_topic', None)
        self.rate_hz = planner_cfg.get('rate', 100)  # default 100 Hz
        self.default_output = planner_cfg.get('default_output', 0.0)

        # --- Load planner algorithm class dynamically ---
        algo_path = os.path.expanduser(f'~/exo_stack_resources/planner/{self.planner_algorithm_name}.py')
        spec_algo = importlib.util.spec_from_file_location(self.planner_algorithm_name, algo_path)
        algo_module = importlib.util.module_from_spec(spec_algo)
        spec_algo.loader.exec_module(algo_module)
        PlannerClass = getattr(algo_module, self.planner_algorithm_name)
        
        # --- Initialize algorithm object ---
        self.planner_obj = PlannerClass()
        
        # --- Internal state ---
        self.profile_active = False
        self.active_profile = None
        self.buffer_profile = None
        self.profile_start_time = 0.0
        self.profile_end_time = 0.0
        self.profile_emergency_stop = 0
        self.time_argument = 0.0
        self.gait_phase = 0.0
        self.start_time = 0
        self.profile_number = 0   
        self.cycle_number = 0     
        
        # --- QoS ---
        qos = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)
        
        # --- Subscribers ---
        self.gait_event_sub = self.create_subscription(Int32, self.gait_event_topic, self.gait_event_callback, qos)
        self.profile_sub = self.create_subscription(Float32MultiArray, self.profile_topic, self.profile_callback, qos)
        if self.approach == 'gait_phase_based' and self.gait_phase_topic:
            self.gait_phase_sub = self.create_subscription(Float32, self.gait_phase_topic, self.gait_phase_callback, qos)

        self.manual_mode_topic = f"/{planner_key}/manual_mode"
        self.manual_cmd_topic = f"/{planner_key}/manual_cmd"

        # --- Subscribers for manual mode ---
        self.manual_mode_sub = self.create_subscription(
            Int32, self.manual_mode_topic, self.manual_mode_callback,
            qos)
        
        self.manual_cmd_sub = self.create_subscription(
            Float32, self.manual_cmd_topic, self.manual_command_callback,
            qos)
        
        # --- Publisher ---
        self.cmd_pub = self.create_publisher(Float32, self.output_topic, qos)

        # --- Publisher for profile status (profile_number + cycle_number) ---
        self.status_topic = f"/{planner_key}/profile_status"
        self.status_pub = self.create_publisher(Float32MultiArray, self.status_topic, qos)

        # --- Timer ---
        self.timer = self.create_timer(1.0/self.rate_hz, self.timer_callback)

        self.get_logger().info(f"Planner '{planner_key}' initialized.")

    # --- Callbacks ---
    def gait_event_callback(self, msg: Int32):
        if msg.data == 1:
            self.get_logger().info("GAIT EVENT RECEIVED")

            # If new profile waiting, activate it on first gait event
            if not self.profile_active and self.active_profile is not None:
                self.profile_active = True
                self.start_time = int(time.time() * 1000)  # milliseconds

            # Increment cycles only for HIL mode (profile_number > 0)
            if self.profile_number > 0 and self.profile_active:
                self.cycle_number += 1
            else:
                self.cycle_number = 0  # Always 0 in deployment

            # Publish status: [profile_number, cycle_number]
            status_msg = Float32MultiArray()
            status_msg.data = [float(self.profile_number), float(self.cycle_number)]
            self.status_pub.publish(status_msg)

            self.get_logger().info(
                f"Published status: profile={self.profile_number}, cycle={self.cycle_number}"
            )

    
    def manual_mode_callback(self, msg: Int32):
        if msg.data == 1 and not self.manual_mode_active:
            self.get_logger().info("Manual mode ENABLED")
            self.manual_mode_active = True

        elif msg.data == 0 and self.manual_mode_active:
            self.get_logger().info("Manual mode DISABLED, resetting profiles")
            self.manual_mode_active = False
            # Reset profiles for clean restart
            self.active_profile = None
            self.buffer_profile = None
            self.profile_active = False

    def manual_command_callback(self, msg: Float32):
        # Always update command value, even if manual mode is off
        self.manual_command_val = float(msg.data)

    def profile_callback(self, msg: Float32MultiArray):
        self.get_logger().info(f"PROFILE CALLBACK RECEIVED")
        self.new_buffer=True
        data = list(msg.data)
        if len(data) < 5:
            self.get_logger().warn("Profile too short, ignoring.")
            return

        profile_number_encoded=data[0] #iteration/candidate no. for HIL mode; dummy in DEPLOYMENT mode
        self.profile_number = int(profile_number_encoded)

        # Reset cycle counter if new profile (only for HIL mode)
        if self.profile_number > 0:
            self.cycle_number = 0
        
        profile_type_encoded = int(data[1])  # 1 = time/value for LIST, 2 = coefficients for FUNCTION
        start_time = data[2]
        end_time = data[-2]
        emergency_stop = data[-1]

        if profile_type_encoded == 1.0:
            if self.planner_algorithm_name.endswith("List"):
                # Time/value pairs: convert to [[t1,p1],[t2,p2],...]
                t_p_flat = data[3:-2]
                if len(t_p_flat) % 2 == 0:
                    profile_nested = [[t_p_flat[i], t_p_flat[i+1]] for i in range(0, len(t_p_flat), 2)]
                    self.buffer_profile = {
                        'profile_number': profile_number_encoded,
                        'profile': profile_nested,
                        'start_time': start_time,
                        'end_time': end_time,
                        'emergency_stop': emergency_stop
                    }
                else:
                    self.get_logger().warn("[Time,value] list has odd length.")
                    
            
            else:
                 self.get_logger().warn("Mismatch between profile type and planner algorithm. Check that both are either List or Function Type")

        elif profile_type_encoded == 2:
            if self.planner_algorithm_name.endswith("Function"):
                # Coefficients: everything between start and end time
                coeffs = data[3:-2]
                self.buffer_profile = {
                    'profile_number': profile_number_encoded,
                    'profile': coeffs,
                    'start_time': start_time,
                    'end_time': end_time,
                    'emergency_stop': emergency_stop
                }
            else:
                self.get_logger().warn("Mismatch between profile type and planner algorithm. Check that both are either List or Function Type")
        else:
            self.get_logger().warn("Profile contains invalid type id")

        
        self.profile_number = int(profile_number_encoded)

        # Reset cycle counter if new profile (only for HIL mode)
        if self.profile_number > 0:
            self.cycle_number = 0


    def gait_phase_callback(self, msg: Float32):
        self.gait_phase = msg.data

    # --- Timer callback ---
    def timer_callback(self):
                
        if self.manual_mode_active:
            # Manual override output
            output_val = float(self.default_output) + float(self.manual_command_val)
            self.cmd_pub.publish(Float32(data=output_val))
            # Optional debug logging
            self.get_logger().info(f"Manual mode: publishing {output_val}")
            return
        
        # --- 1. Emergency stop check ---
        if self.buffer_profile and self.buffer_profile['emergency_stop'] == 1:
            self.profile_active = False  # stop any ongoing execution
            self.active_profile = self.buffer_profile
            self.cmd_pub.publish(Float32(data=float(self.default_output)))
            self.get_logger().info("EMERGENCY STOP: Publishing default output")
            return

        # --- 2. Transfer buffer -> active only if no profile is executing ---
        if not self.profile_active and self.buffer_profile and self.new_buffer:
            self.active_profile = self.buffer_profile
            self.new_buffer=False
            self.get_logger().info("Transferred buffer profile to active profile")

        # --- 3. Determine time argument ---
        if self.approach == 'time_based':
            self.time_argument = int(time.time() * 1000) - self.start_time
        else:
            self.time_argument = self.gait_phase

        # --- 4. Update planner object and publish command ---
        if self.active_profile:
            self.planner_obj.profile = self.active_profile['profile']

            if self.time_argument < self.active_profile['start_time']:
                # Before profile start → publish default output
                self.cmd_pub.publish(Float32(data=float(self.default_output)))
                # self.get_logger().info("Before start time: Publishing default output")
            elif self.time_argument > self.active_profile['end_time']:
                # After profile end → mark inactive and publish default output
                self.profile_active = False
                self.cmd_pub.publish(Float32(data=float(self.default_output)))
                # self.get_logger().info("After end time: Publishing default output and stopping execution")
            else:
                # During execution → compute and publish next planner command
                cmd_val = self.planner_obj.next_point(self.time_argument)
                self.cmd_pub.publish(Float32(data=float(cmd_val)))
                # self.get_logger().info(f"Executing planner: cmd_val={cmd_val}")
        else:
            # No active profile → publish default output
            self.cmd_pub.publish(Float32(data=float(self.default_output)))
            self.get_logger().info("No active profile: Publishing default output")




def main(args=None):
    rclpy.init(args=args)
    if len(sys.argv) < 2:
        raise RuntimeError("No planner key specified")
    planner_key = sys.argv[1]
    node = GenericPlannerNode(planner_key)

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
