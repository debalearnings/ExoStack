class Builder1_Coefficients:
    def __init__(self):
        # These can be set externally after object creation
        self.profile_start_time_or_phase = 0.0
        self.profile_end_time_or_phase = 0.0

    def buildprofile(self, values):
        """
        Build a coefficient-type profile.

        Args:
            values (list): list of coefficients [c0, c1, c2, ...]

        Returns:
            list: [2.0, start_time, c0, c1, ..., cn, end_time]
        """
        if not isinstance(values, list):
            raise ValueError("Input must be a list of coefficients")

        profile = [2.0]  # 0 indicates coefficient-type profile
        profile.append(self.profile_start_time_or_phase)
        profile.extend(values)
        profile.append(self.profile_end_time_or_phase)

        return profile
