# util/sensor_util.py

import yaml
import os

class SensorUtil:
    def __init__(self, config_path: str = None, hub_sensor_list=None):
        """
        Loads the sensors.yaml config file which defines the hub → sensors mapping.
        Example sensors.yaml:
        hubs:
          hub1:
            sensors: [imu, emg, fsr]
          hub2:
            sensors: [imu, encoder]
        """
        # Default path in ~/exo_stack_resources/config/sensors.yaml
        if config_path is None:
            config_path = os.path.expanduser("~/exo_stack_resources/config/sensors.yaml")

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Flatten sensor indices across hubs in order
        self.sensor_index_map = {}
        current_index = 0
        hubs = self.config.get("hubs", {})
        for hub_name, hub_data in hubs.items():
            sensors = hub_data.get("sensors", [])
            for sensor in sensors:
                # Store mapping: (hub, sensor) → index
                self.sensor_index_map[(hub_name, sensor)] = current_index
                current_index += 1

        # Store hub_sensor_list once during initialization
        self.hub_sensor_list = hub_sensor_list if hub_sensor_list is not None else []

    def get_sensor_value(self, all_sensor_values):
        """
        Extracts sensor values for the requested hub/sensor pairs.

        Args:
            all_sensor_values: list of all sensor values (flattened across hubs)

        Returns:
            List of corresponding sensor values in the same order as hub_sensor_list
        """
        values = []
        for hub_name, sensor_name in self.hub_sensor_list:
            idx = self.sensor_index_map.get((hub_name, sensor_name))
            if idx is None:
                raise ValueError(f"Sensor {sensor_name} in {hub_name} not found in config!")
            if idx >= len(all_sensor_values):
                raise IndexError(
                    f"Index {idx} out of range for all_sensor_values with length {len(all_sensor_values)}"
                )
            values.append(all_sensor_values[idx])
        return values

