class Builder_Nwaypoint_List:
    def __init__(self):
        # Can be set externally after object creation
        self.default_value = 20.0

    def buildprofile(self, values):
        """
        Build a list-type profile from an arbitrary number of waypoints.

        Args:
            values (list): [start, t1, v1, t2, v2, ..., tN, vN, end]

                start  : start of the time / gait-phase domain
                ti, vi : i-th waypoint (time-or-phase, value), strictly increasing in ti
                end    : end of the time / gait-phase domain

                Length must be even and at least 4, i.e. 2*N + 2 for N waypoints.
                N = 1 reproduces Builder1_List, N = 2 reproduces Builder2_List.

        Returns:
            list: encoded list-type profile:
            [1, start, start, default, t1, v1, t2, v2, ........, tN, vN, end, default, end]

        Raises:
            ValueError: on malformed input (bad length, non-numeric, non-monotonic
                        times, waypoints outside [start, end], or start >= end)
        """
        # ---- structural validation -------------------------------------------------
        if not isinstance(values, (list, tuple)):
            raise ValueError("Input must be a list (or tuple) of numbers.")

        if len(values) < 4 or len(values) % 2 != 0:
            raise ValueError(
                "Input must have even length >= 4, i.e. 2*N + 2 for N waypoints: "
                "[start, t1, v1, ..., tN, vN, end]. Got length %d." % len(values)
            )

        try:
            vals = [float(v) for v in values]
        except (TypeError, ValueError):
            raise ValueError("All elements of the input must be numeric.")

        start = vals[0]
        end = vals[-1]
        flat = vals[1:-1]                       # the 2*N waypoint numbers
        n_wp = len(flat) // 2

        # ---- domain validation -----------------------------------------------------
        if not (start < end):
            raise ValueError(
                "start (%g) must be strictly less than end (%g)." % (start, end)
            )

        times = flat[0::2]
        vals_wp = flat[1::2]

        # strictly increasing times: both interpolating planners divide by (t1 - t0)
        for i in range(n_wp - 1):
            if not (times[i] < times[i + 1]):
                raise ValueError(
                    "Waypoint times must be strictly increasing; "
                    "waypoint %d (t=%g) is not before waypoint %d (t=%g)."
                    % (i + 1, times[i], i + 2, times[i + 1])
                )

        # waypoints must lie inside the declared domain
        for i, t in enumerate(times):
            if t < start or t > end:
                raise ValueError(
                    "Waypoint %d time (%g) lies outside the domain [%g, %g]."
                    % (i + 1, t, start, end)
                )

        # ---- assemble waypoint list -------------------------------------------------
        # Anchor at default_value on each side, exactly like Builder1/Builder2. The
        # anchor is skipped when the user already supplies a waypoint at that instant,
        # otherwise the profile would contain two points with the same time and the
        # planner would divide by zero while interpolating.
        points = []

        if times[0] > start:
            points.append((start, self.default_value))

        for t, v in zip(times, vals_wp):
            points.append((t, v))

        if times[-1] < end:
            points.append((end, self.default_value))

        # ---- encode -----------------------------------------------------------------
        profile = [1.0]          # 1 indicates list-type profile
        profile.append(start)    # domain start
        for t, v in points:
            profile.extend([t, v])
        profile.append(end)      # domain end

        return profile