from cmaes import CMA
import numpy as np

class OPT_CMA_ES:
    def __init__(self,
                 mean=None,
                 bounds=None,
                 sigma=0.5,
                 n_max_resampling=1,
                 maximize=False,
                 max_generations=None,
                 population_size=None):
        """
        CMA-ES optimizer wrapper.

        Args:
            mean (list): Initial mean of search distribution. REQUIRED.
            bounds (list): Bounds for search space [[low, high], ...]. REQUIRED.
            sigma (float): Initial std. deviation. Default = 0.5.
            n_max_resampling (int): Max resampling attempts. Default = 1.
            maximize (bool): If True, maximize objective. Default = False.
            max_generations (int): Maximum number of generations. Default = None (no limit).
            population_size (int): Population size. If None, CMA-ES default is used.
        """
        if mean is None or bounds is None:
            raise ValueError("CMA-ES requires 'mean' and 'bounds' hyperparameters")

        self.optimizer = CMA(
            mean=np.array(mean, dtype=float),
            bounds=np.array(bounds, dtype=float),
            sigma=sigma,
            n_max_resampling=n_max_resampling,
            population_size=population_size
        )
        self.current_generation = []
        self.pending_results = []
        self.generation_index = 0
        self.maximize = maximize
        self.max_generations = max_generations

        # Iterator pointer for point-wise usage
        self._gen_pointer = 0

        # Track best-so-far
        self.best_point = None
        self.best_score = -np.inf if maximize else np.inf

    # -------------------------
    # Generation-based interface
    # -------------------------
    def start_generation(self):
        """Generate a full population (one generation)."""
        self.current_generation = [self.optimizer.ask() for _ in range(self.optimizer.population_size)]
        self.pending_results = []
        self._gen_pointer = 0  # reset pointer
        return self.current_generation

    def generation_complete(self):
        return len(self.pending_results) == self.optimizer.population_size

    def finalize_generation(self):
        if not self.generation_complete():
            raise RuntimeError("Not all candidates evaluated yet!")
        self.optimizer.tell(self.pending_results)
        self.generation_index += 1

    # -------------------------
    # Point-wise interface (for HIL node)
    # -------------------------
    def get_next_candidate(self):
        """Return one candidate at a time, managing generations internally."""
        if self.max_generations is not None and self.generation_index >= self.max_generations:
            return None  # stop suggesting after max generations

        if not self.current_generation or self._gen_pointer >= len(self.current_generation):
            # Start a new generation
            self.start_generation()
        candidate = self.current_generation[self._gen_pointer]
        self._gen_pointer += 1
        return [float(x) for x in candidate]

    def submit_result(self, point, cost):
        """Submit result for a single candidate."""
        score = -cost if self.maximize else cost
        self.pending_results.append((point, score))

        # Update best-so-far
        if self.maximize:
            if cost > self.best_score:
                self.best_score = cost
                self.best_point = point
        else:
            if cost < self.best_score:
                self.best_score = cost
                self.best_point = point

        # If generation is complete → update CMA-ES
        if self.generation_complete():
            self.finalize_generation()

    # -------------------------
    def get_best_so_far(self):
        if self.best_point is None:
            return None, None
        return [float(x) for x in self.best_point], float(self.best_score)

    def is_done(self):
        """Check if maximum generations reached."""
        if self.max_generations is None:
            return False
        return self.generation_index >= self.max_generations
