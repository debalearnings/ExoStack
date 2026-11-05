# LinearInterpolatedList.py

class LinearInterpolatedList:
    """
    Linear interpolated list planner.

    Usage:
        planner = LinearInterpolatedList()
        planner.profile = [[t1, p1], [t2, p2], ...]  # assign profile list before using
        value = planner.next_point(current_time_or_gait_percent)
    """

    def __init__(self):
        # Profile list of [time_or_percent, value] pairs
        self.profile = None

    def next_point(self, t):
        """
        Get interpolated value for given t (time or gait percent).

        Args:
            t (float): current time or gait percentage

        Returns:
            float: interpolated value
        """

        if self.profile is None:
            raise ValueError("Profile not set. Assign profile before calling next_point.")
        if len(self.profile) < 2:
            raise ValueError("Profile list must contain at least 2 points.")

        # Clamp t to profile range
        if t <= self.profile[0][0]:
            return self.profile[0][1]
        if t >= self.profile[-1][0]:
            return self.profile[-1][1]

        # Find the interval [t_i, t_{i+1}] where t falls
        for i in range(len(self.profile) - 1):
            t0, p0 = self.profile[i]
            t1, p1 = self.profile[i + 1]
            if t0 <= t <= t1:
                # Linear interpolation
                ratio = (t - t0) / (t1 - t0)
                value = p0 + ratio * (p1 - p0)
                return value

