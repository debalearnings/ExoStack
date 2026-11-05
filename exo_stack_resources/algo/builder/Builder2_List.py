class Builder2_List:
    def __init__(self):
        # Can be set externally after object creation
        self.default_value = 20.0

    def buildprofile(self, values):
        """
        Build a list-type profile (Builder2 style).

        Args:
            values (list): [start_time_or_phase, peak1_time_or_phase, peak1_value, peak2_time_or_phase, peak2_value, end_time_or_phase]

        Returns:
            list: [1, start, start, default, peak1_time, peak1_value, peak2_time, peak2_value, end, default, end]
        """
        if not isinstance(values, list) or len(values) != 6:
            raise ValueError("Input must be a list of 6 elements: [start, peak1_time, peak1_value, peak2_time, peak2_value, end]")

        start, peak1_time, peak1_value, peak2_time, peak2_value, end = values

        profile = [1.0]  # 1 indicates list-type profile
        profile.extend([
            start, start, self.default_value,
            peak1_time, peak1_value, peak2_time, peak2_value,
            end, self.default_value, end
        ])

        return profile