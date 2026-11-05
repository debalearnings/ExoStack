import json

class Lookup_Speed_Intent_Segmentwise:
    def __init__(self, json_path):
        with open(json_path, "r") as f:
            self.lookup_data = json.load(f)

    def readlookuptable(self, args):
        """
        Args:
            args (list): [speed_value, intent_label]

        Returns:
            list corresponding to the nearest/clamped speed-intent pair
        """
        if not isinstance(args, list) or len(args) != 2:
            raise ValueError("Expected [speed_value, intent_label]")

        speed_value = float(args[0])
        intent_label = str(args[1])

        if intent_label not in self.lookup_data:
            raise KeyError(f"Intent {intent_label} not found in lookup table")

        intent_data = self.lookup_data[intent_label]

        # Case 1: intent_data is already a list (no speed subclasses)
        if isinstance(intent_data, list):
            return intent_data

        # Case 2: intent_data is a dict with speed subclasses
        if not intent_data:  # empty dict
            raise KeyError(f"No data available for intent {intent_label}")

        # Convert available speed keys to floats
        speeds = sorted([float(k) for k in intent_data.keys()])

        # Clamp and nearest
        if speed_value <= speeds[0]:
            nearest_speed = speeds[0]
        elif speed_value >= speeds[-1]:
            nearest_speed = speeds[-1]
        else:
            nearest_speed = min(speeds, key=lambda s: abs(s - speed_value))

        return intent_data[str(nearest_speed)]
