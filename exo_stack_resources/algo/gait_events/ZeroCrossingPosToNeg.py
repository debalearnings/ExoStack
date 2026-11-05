class ZeroCrossingPosToNeg:
    """
    Stateful positive-to-negative zero crossing detector.
    Row-by-row streaming with sliding window and fraction-based last elements check.
    """

    def __init__(self, window_size=10, parameters=None):
        self.window_size = window_size
        self.fraction = 0.2  # fraction of window that must be consecutive positive at end
        
        if parameters is not None:
            if len(parameters) > 0:
                self.fraction = parameters[0]

        self.window = []
        self.state = None  # initial state is None

    def detect(self, new_row):
        """
        new_row: [value] (1D list)
        Returns 1 if zero crossing detected, else 0.
        """
        # Append new row and maintain window
        self.window.append(new_row)
        if len(self.window) > self.window_size:
            self.window.pop(0)

        # Wait until window is fully populated
        if len(self.window) < self.window_size:
            return 0  # state remains None until full window

        event = 0

        # Count consecutive negatives at the end
        consecutive_negative_count = 0
        for row in reversed(self.window):
            if row[0] < 0:
                consecutive_negative_count += 1
            else:
                break  # stop counting at first non-negative

        consecutive_fraction = consecutive_negative_count / self.window_size

        # Trigger event if previous state was positive and fraction threshold met
        if self.state == 'positive' and consecutive_fraction >= self.fraction:
            event = 1
            self.state = 'not_all_positive'  # mark that crossing has occurred

        # Update state if entire window is positive, but only if state is already not None
        if all(row[0] > 0 for row in self.window):
            self.state = 'positive'

        return event
