from bayes_opt import BayesianOptimization, UtilityFunction

class OPT_BAYESIAN:
    def __init__(self,
                 pbounds=None,
                 maximize=True,
                 max_iters=None,
                 random_state=1,
                 kind="ei",
                 xi=0.02,
                 kappa=2.576):
        """
        Bayesian Optimization wrapper.

        Args:
            pbounds (dict): Parameter bounds, e.g. {"x": (-5,5), "y": (-3,3)}. REQUIRED.
            maximize (bool): If True, maximize objective. If False, minimize.
            max_iters (int): Maximum number of iterations (candidates). Default = None (no limit).
            random_state (int): RNG seed.
            kind (str): Acquisition function type: "ei", "poi", or "ucb".
            xi (float): Exploration parameter for EI/POI.
            kappa (float): Exploration parameter for UCB.
        """
        if pbounds is None:
            raise ValueError("Bayesian optimization requires 'pbounds' hyperparameter")

        self.maximize = maximize
        self.param_names = list(pbounds.keys())
        self.max_iters = max_iters
        self.iter_count = 0  # Track iterations

        self.optimizer = BayesianOptimization(
            f=None,
            pbounds=pbounds,
            random_state=random_state
        )

        # Select acquisition function with correct params
        if kind in ["ei", "poi"]:
            self.utility = UtilityFunction(kind=kind, xi=xi)
        elif kind == "ucb":
            self.utility = UtilityFunction(kind=kind, kappa=kappa)
        else:
            raise ValueError(f"Unknown acquisition kind '{kind}'. Must be 'ei', 'poi', or 'ucb'.")

        # Track best-so-far
        self.best_point = None
        self.best_score = -float("inf") if maximize else float("inf")

    def get_next_candidate(self):
        """Suggest next candidate point as list of floats, unless max_iters reached."""
        if self.max_iters is not None and self.iter_count >= self.max_iters:
            return None  # No more candidates

        suggestion = self.optimizer.suggest(self.utility)
        self.iter_count += 1
        return [float(suggestion[p]) for p in self.param_names]

    def submit_result(self, params, cost):
        """
        Submit evaluation result.

        Args:
            params (list): Candidate parameters as list (same order as pbounds).
            cost (float): Cost function value.
        """
        param_dict = dict(zip(self.param_names, params))
        score = cost if self.maximize else -cost
        self.optimizer.register(params=param_dict, target=score)

        # Update best-so-far
        if self.maximize:
            if cost > self.best_score:
                self.best_score = cost
                self.best_point = params
        else:
            if cost < self.best_score:
                self.best_score = cost
                self.best_point = params

    def get_best_so_far(self):
        """Return (point, score) with floats."""
        if self.best_point is None:
            return None, None
        return [float(x) for x in self.best_point], float(self.best_score)

    def is_done(self):
        """Check if maximum iterations reached."""
        if self.max_iters is None:
            return False
        return self.iter_count >= self.max_iters
