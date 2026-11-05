from numpy.polynomial import Polynomial
import numpy as np

class CubicPolynomialFunction:
    """
    Cubic polynomial motion profile evaluator.

    The cubic polynomial is defined as:
        y(t) = a*t^3 + b*t^2 + c*t + d

    Usage:
        obj = CubicPolynomialFunction()
        obj.coeffs = [d, c, b, a]  # ascending order: constant -> cubic
        y = obj.next_point(t)
    """
    def __init__(self):
        self.coeffs = None            # list of 4 coefficients: [d, c, b, a]
        self._polynomial = None       # Polynomial object
        self._last_coeffs = None      # to track updates

    def _create_polynomial(self):
        """Create Polynomial object from current coefficients."""
        
        self._polynomial = Polynomial(self.coeffs)
        # store copy for change detection
        self._last_coeffs = self.coeffs.copy()

    def next_point(self, t):
        """
        Evaluate cubic polynomial at time/gait percentage t.
        Regenerates polynomial if coefficients were updated.
        """
        if self.coeffs is None:
            raise ValueError("Coeffs not set. Assign coeffs before calling next_point.")
        
        if self.coeffs is None or len(self.coeffs) != 4:
            raise ValueError("Coeffs must be a list of 4 numbers [d, c, b, a].")
        
        # check if polynomial needs to be created or updated
        if self._polynomial is None or self.coeffs != self._last_coeffs:
            self._create_polynomial()

        return float(self._polynomial(t))
