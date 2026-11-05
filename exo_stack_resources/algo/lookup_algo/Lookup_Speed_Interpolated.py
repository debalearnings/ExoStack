import json
import bisect

class Lookup_Speed_Interpolated:
    def __init__(self, json_path):
        with open(json_path, "r") as f:
            self.lookup_data = json.load(f)
        # Convert keys to floats for interpolation
        self.speeds = sorted([float(k) for k in self.lookup_data.keys()])

    def readlookuptable(self, args):
        """
        Args:
            args (list): [speed] or [speed, _]
        Returns:
            list interpolated for the given speed
        """
        if not isinstance(args, list) or len(args) not in [1, 2]:
            raise ValueError("Expected [speed] or [speed, something]")

        speed = float(args[0])  # take first element always

        # If exact match exists
        if str(speed) in self.lookup_data:
            return self.lookup_data[str(speed)]

        # Otherwise, interpolate
        idx = bisect.bisect_left(self.speeds, speed)

        if idx == 0:  # below range
            return self.lookup_data[str(self.speeds[0])]
        elif idx == len(self.speeds):  # above range
            return self.lookup_data[str(self.speeds[-1])]
        else:
            # interpolate between speeds[idx-1] and speeds[idx]
            s1, s2 = self.speeds[idx-1], self.speeds[idx]
            v1 = self.lookup_data[str(s1)]
            v2 = self.lookup_data[str(s2)]

            # linear interpolation
            ratio = (speed - s1) / (s2 - s1)
            return [v1[i] + ratio * (v2[i] - v1[i]) for i in range(len(v1))]
