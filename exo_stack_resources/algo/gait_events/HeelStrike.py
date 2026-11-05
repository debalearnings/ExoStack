class HeelStrike:
    """
    Stateful heel-strike detector based on thresholded FSR signals.
    Row-by-row streaming with sliding window, fraction-based rising edge detection.
    """



    def __init__(self, window_size=10, parameters=None):
        """
        parameters: list containing [threshold, fraction] in order
        """
        self.window_size = window_size

        # Default values
        self.threshold = 0.5
        self.fraction = 0.2

        if parameters is not None:
            if len(parameters) > 0:
                self.threshold = parameters[0]
            if len(parameters) > 1:
                self.fraction = parameters[1]

        self.window = []     # sliding window
        self.state = None    # initial state

    def detect(self, new_row):
        """
        new_row: [value] (1D list)
        Returns 1 if rising edge (heel-strike) detected, else 0.
        """
        # Convert raw value to 0 or 1
        value_bin = 1 if new_row[0] > self.threshold else 0

        # Append to window
        self.window.append([value_bin])
        if len(self.window) > self.window_size:
            self.window.pop(0)

        # Wait until window is fully populated
        if len(self.window) < self.window_size:
            return 0

        event = 0

        # Count consecutive 1s at the end
        consecutive_ones = 0
        for row in reversed(self.window):
            if row[0] == 1:
                consecutive_ones += 1
            else:
                break

        consecutive_fraction = consecutive_ones / self.window_size

        # Trigger event only if previous state was 'low'
        if self.state == 'low' and consecutive_fraction >= self.fraction:
            event = 1
            self.state = 'not_all_low'  # mark that heel-strike occurred

        # Update state if all zeros in window
        if all(row[0] == 0 for row in self.window):
            self.state = 'low'

        return event
