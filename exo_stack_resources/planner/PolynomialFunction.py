from numpy.polynomial import Polynomial
import numpy as np

class PolynomialFunction:
    """
    Generic polynomial motion profile evaluator.

    The polynomial is defined as:
        y(t) = c0 + c1*t + c2*t^2 + ... + cn*t^n

    Usage:
        obj = PolynomialFunction()
        obj.coeffs = [c0, c1, c2, c3]  # constant -> cubic
        y = obj.next_point(t)
    """
    def __init__(self):
        self.coeffs = None            # list of polynomial coefficients [c0, c1, ..., cn]
        self._polynomial = None       # Polynomial object
        self._last_coeffs = None      # to track updates

    def _create_polynomial(self):
        """Create Polynomial object from current coefficients."""
        
        self._polynomial = Polynomial(self.coeffs)
        # store copy for change detection
        self._last_coeffs = self.coeffs.copy()

    def next_point(self, t):
        """
        Evaluate polynomial at time/gait percentage t.
        Regenerates polynomial if coefficients were updated.
        """
        if self.coeffs is None:
            raise ValueError("Coeffs not set. Assign coeffs before calling next_point.")
        
        if self.coeffs is None or len(self.coeffs) < 1:
            raise ValueError("Coeffs must be a non-empty list of numbers.")
        
        if self._polynomial is None or self.coeffs != self._last_coeffs:
            self._create_polynomial()

        return float(self._polynomial(t))
