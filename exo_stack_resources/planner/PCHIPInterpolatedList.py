from scipy.interpolate import PchipInterpolator
import numpy as np

class PCHIPInterpolatedList:
    
    """
    PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) interpolator for motion profiles.
    
    Usage:
        obj = PCHIPInterpolatedList()
        obj.profile = [[t0, p0], [t1, p1], ...]   # Assign profile before using
        value = obj.next_point(gait_time)
    """
    def __init__(self):
        self.profile = None          # Current profile assigned externally
        self._interpolator = None    # Internal PCHIP interpolator
        self._last_profile = None    # Copy of profile used to create interpolator

    def _create_interpolator(self):
        """Generate PCHIP interpolator from current profile."""
        

        times = np.array([p[0] for p in self.profile], dtype=float)
        positions = np.array([p[1] for p in self.profile], dtype=float)

        self._interpolator = PchipInterpolator(times, positions)
        # Store a deep copy for change detection
        self._last_profile = [p[:] for p in self.profile]

    def next_point(self, t):
        """
        Get interpolated value at time/gait percentage t.
        Regenerates interpolator if profile was updated.
        """
        if self.profile is None:
            raise ValueError("Profile not set. Assign profile before calling next_point.")
        
        if not len(self.profile) < 2:
            raise ValueError("Profile must have at least 2 points.")

        # Check if profile has changed
        if self._interpolator is None or self.profile != self._last_profile:
            self._create_interpolator()

        # Clamp input to profile bounds
        t_clamped = np.clip(t, self.profile[0][0], self.profile[-1][0])
        return float(self._interpolator(t_clamped))
