"""Optimizers that propose the next experiment to run.

All optimizers share the same interface: given the history of past experiments,
suggest the next set of parameters. This lets the closed loop swap one optimizer
for another without changing anything else.
"""

import numpy as np
import warnings
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings("ignore", category=ConvergenceWarning)

class RandomSearch:
    """The honest baseline: pick a random point within the parameter bounds."""

    name = "random_search"

    def __init__(self, bounds, rng):
        # bounds = {"param_name": (low, high), ...}
        # rng = random-number generator (for reproducibility)
        self.bounds = bounds
        self.rng = rng

    def suggest(self, history):
        # history = list of past experiments (random search ignores it).
        params = {}
        for name, (low, high) in self.bounds.items():
            # TASK: draw a uniform random value between low and high.
            # Hint: self.rng.uniform(low, high) gives one random number in [low, high].
            params[name] = self.rng.uniform(low, high)  # replace this
        return params
    
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel, WhiteKernel
from scipy.stats import norm


class BayesianOptimizer:
    """Gaussian-process + Expected-Improvement optimizer.

    Uses past (params, score) pairs to fit a surrogate model of the landscape,
    then picks the next point with the highest Expected Improvement.
    """

    name = "bayesian_optimization"

    def __init__(self, bounds, rng, n_init=5, n_candidates=512):
        self.bounds = bounds
        self.rng = rng
        self.names = list(bounds.keys())
        self.low = np.array([bounds[n][0] for n in self.names])
        self.high = np.array([bounds[n][1] for n in self.names])
        self.n_init = n_init              # random experiments before BO kicks in
        self.n_candidates = n_candidates  # how many candidate points to score

    def _to_array(self, params):
        # turn a params dict into a plain number array, in a fixed order
        return np.array([params[n] for n in self.names])

    def _to_params(self, x):
        # turn a number array back into a params dict
        return {n: float(v) for n, v in zip(self.names, x)}
    
    def _normalize(self, x):
        # real values -> [0, 1]
        return (x - self.low) / (self.high - self.low)

    def _denormalize(self, u):
        # [0, 1] -> real values
        return self.low + u * (self.high - self.low)

    def _random_point(self):
        x = self.rng.uniform(self.low, self.high)
        return self._to_params(x)

    def suggest(self, history):
        # Collect successful past experiments (those with a real score).
        observed = [(self._to_array(h['params']), h['score'])
                    for h in history if h['score'] is not None]
        
        # Also collect FAILED experiments' locations. They have no score, but we
        # use them to steer the optimizer AWAY from failure regions.
        failed = [self._to_array(h['params'])
                  for h in history if h['score'] is None]

        # Phase 1: not enough data yet -> explore randomly to seed the model.
        if len(observed) < self.n_init:
            return self._random_point()

        # Phase 2: fit the GP surrogate on what we know.
        # Normalize inputs to [0,1] so the GP treats all parameters on the same
        # scale. Without this, parameters with huge ranges (thickness ~thousands)
        # dominate ones with small ranges (time ~tens), and the GP fails to fit.
        X = np.array([self._normalize(x) for x, _ in observed])
        y = np.array([s for _, s in observed])

        kernel = (ConstantKernel(1.0) * Matern(length_scale=np.ones(len(self.names)), nu=2.5)
                  + WhiteKernel(noise_level=0.01))
        gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True)
        gp.fit(X, y)

        # Generate random candidate points and predict mean + uncertainty.
        # Candidates live in normalized [0,1] space, same as the GP's inputs.
        candidates = self.rng.uniform(0.0, 1.0, size=(self.n_candidates, len(self.names)))
        mu, sigma = gp.predict(candidates, return_std=True)
        sigma = np.maximum(sigma, 1e-9)   # avoid divide-by-zero

        # Expected Improvement over the best score seen so far.
        best = y.max()
        z = (mu - best) / sigma
        ei = (mu - best) * norm.cdf(z) + sigma * norm.pdf(z)

        # Soft feasibility penalty: down-weight candidates close to known failures.
        # A candidate sitting right on top of a past failure gets its EI crushed.
        if failed:
            failed_arr = np.array([self._normalize(f) for f in failed])

            for j in range(len(failed_arr)):
                # both candidates and failures are already in [0,1] space
                d = np.linalg.norm(candidates - failed_arr[j], axis=1)
                penalty = 1.0 - np.exp(-(d ** 2) / (2 * 0.15 ** 2))
                ei = ei * penalty

        # Pick the candidate with the highest EI.
        best_idx = int(np.argmax(ei))
        chosen_real = self._denormalize(candidates[best_idx])
        return self._to_params(chosen_real)