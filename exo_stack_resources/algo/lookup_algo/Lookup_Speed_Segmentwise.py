import json

class Lookup_Speed_Segmentwise:
    def __init__(self, json_path):
        with open(json_path, "r") as f:
            self.lookup_data = json.load(f)
        # Store available speeds as floats for comparison
        self.speeds = sorted([float(k) for k in self.lookup_data.keys()])

    def readlookuptable(self, args):
        """
        Args:
            args (list): [speed] or [speed, _]

        Returns:
            list corresponding to the nearest speed class,
            clamped at min/max if out of range
        """
        if not isinstance(args, list) or len(args) not in [1, 2]:
            raise ValueError("Expected [speed] or [speed, something]")

        speed = float(args[0])  # take the first element

        # Clamp if outside the range
        if speed <= self.speeds[0]:
            nearest_speed = self.speeds[0]
        elif speed >= self.speeds[-1]:
            nearest_speed = self.speeds[-1]
        else:
            # Inside range → pick nearest
            nearest_speed = min(self.speeds, key=lambda s: abs(s - speed))

        return self.lookup_data[str(nearest_speed)]
