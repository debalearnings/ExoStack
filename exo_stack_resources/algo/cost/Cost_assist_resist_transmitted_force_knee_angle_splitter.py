import numpy as np

class Cost_assist_resist_transmitted_force_knee_angle_splitter:
    def __init__(self, resistive_force_threshold):
        """
        resistive_force_threshold: peak resistive force threshold beyond which cost is negative
        """
        self.resistive_threshold = resistive_force_threshold

    def compute(self, data_array):
        """
        data_array: numpy array of shape (N, 3)
                    column 0: thigh imu pitch (deg, +backward, -forward)
                    column 1: shank imu pitch (deg, +backward, -forward)
                    column 2: loadcell value (force)
        Returns: cost value
        """
        if data_array.shape[1] != 3:
            raise ValueError("Expected 3 sensors: thigh_pitch, shank_pitch, loadcell")

        thigh = data_array[:, 0]
        shank = data_array[:, 1]
        loadcell = data_array[:, 2]

        # Compute posterior knee angle at each timestep
        # Anatomical angle: 180° when leg straight, <180° when flexed, can exceed 180° if hyperextended
        knee_angle = 180.0 + thigh - shank  # element-wise

        # Find the index of minimum knee angle in the cycle
        min_knee_idx = np.argmin(knee_angle)

        # Split cycle into two phases at min knee angle
        assist_phase = loadcell[:min_knee_idx + 1]  # from start to min_knee_idx
        resist_phase = loadcell[min_knee_idx + 1:]  # from min_knee_idx+1 to end

        # Peak forces in each phase
        peak_assistive_force = np.max(assist_phase) if assist_phase.size > 0 else 0.0
        peak_resistive_force = np.max(resist_phase) if resist_phase.size > 0 else 0.0

        # Determine cost
        if peak_resistive_force > self.resistive_threshold:
            cost = -peak_resistive_force
        else:
            cost = peak_assistive_force

        return float(cost)
