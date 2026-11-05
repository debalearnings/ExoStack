class Builder1_List:
    def __init__(self):
        # Can be set externally after object creation
        self.default_value = 20.0

    def buildprofile(self, values):
        """
        Build a list-type profile (Builder1 style).

        Args:
            values (list): [start_time_or_phase, peak_time_or_phase, peak_value, end_time_or_phase]

        Returns:
            list: [1.0, start, start, default, peak_time, peak_value, end, default, end]
        """
        if not isinstance(values, list) or len(values) != 4:
            raise ValueError("Input must be a list of 4 elements: [start, peak_time, peak_value, end]")

        start, peak_time, peak_value, end = values

        profile = [1.0]  # 1 indicates list-type profile
        profile.extend([
            start, start, self.default_value,
            peak_time, peak_value,
            end, self.default_value, end
        ])

        return profile
