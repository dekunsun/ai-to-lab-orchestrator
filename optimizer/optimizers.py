"""Optimizers that propose the next experiment.

Two strategies, same interface, so the benchmark can compare them fairly:

  * RandomSearch  — samples uniformly in bounds. The honest baseline.
  * BayesianOptimizer — Gaussian-process surrogate + Expected Improvement.
        A transparent ~self-contained BO (sklearn GP) rather than a black box,
        so every step is explainable in an interview.

Both must cope with the lab returning FAILURES: a failed experiment yields no
objective value, so it is not used to condition the surrogate. We still count
it against the experiment budget (failures cost real lab time).
"""

from __future__ import annotations
import warnings
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel, WhiteKernel
from sklearn.exceptions import ConvergenceWarning
from scipy.stats import norm


class _ParamSpace:
    def __init__(self, bounds: dict[str, tuple[float, float]]):
        self.names = list(bounds.keys())
        self.lo = np.array([bounds[n][0] for n in self.names], dtype=float)
        self.hi = np.array([bounds[n][1] for n in self.names], dtype=float)

    def sample(self, rng: np.random.Generator) -> dict[str, float]:
        u = rng.random(len(self.names))
        x = self.lo + u * (self.hi - self.lo)
        return {n: float(v) for n, v in zip(self.names, x)}

    def to_unit(self, params: dict[str, float]) -> np.ndarray:
        x = np.array([params[n] for n in self.names], dtype=float)
        return (x - self.lo) / (self.hi - self.lo)

    def from_unit(self, u: np.ndarray) -> dict[str, float]:
        x = self.lo + np.clip(u, 0, 1) * (self.hi - self.lo)
        return {n: float(v) for n, v in zip(self.names, x)}


class RandomSearch:
    name = "random_search"

    def __init__(self, bounds, rng: np.random.Generator):
        self.space = _ParamSpace(bounds)
        self.rng = rng

    def suggest(self, history: list[dict]) -> dict[str, float]:
        return self.space.sample(self.rng)


class BayesianOptimizer:
    name = "bayesian_optimization"

    def __init__(self, bounds, rng: np.random.Generator, n_init: int = 5,
                 n_candidates: int = 512, fail_streak_limit: int = 3):
        self.space = _ParamSpace(bounds)
        self.rng = rng
        self.n_init = n_init
        self.n_candidates = n_candidates
        self.fail_streak_limit = fail_streak_limit

    def suggest(self, history: list[dict]) -> dict[str, float]:
        # successful experiments (valid objective) condition the GP
        obs = [(h["x_unit"], h["y"]) for h in history if h.get("y") is not None]
        # failed experiments are NOT regression targets, but we still use them:
        # the optimizer should learn to avoid regions that produce no data.
        failed = [h["x_unit"] for h in history if h.get("y") is None]

        # Escape hatch: if the last few experiments all failed, the surrogate is
        # stuck in an infeasible region. Force pure exploration to break out.
        # (A real lab optimizer needs this; without it BO can loop on dead zones.)
        recent = history[-self.fail_streak_limit:]
        if len(recent) >= self.fail_streak_limit and all(h.get("y") is None for h in recent):
            return self.space.sample(self.rng)

        # initial design: random until we have enough points to fit a GP
        if len(obs) < self.n_init:
            return self.space.sample(self.rng)

        X = np.array([o[0] for o in obs])
        y = np.array([o[1] for o in obs])

        kernel = (ConstantKernel(1.0, (1e-2, 1e2))
                  * Matern(length_scale=np.ones(X.shape[1]), nu=2.5)
                  + WhiteKernel(noise_level=1e-2, noise_level_bounds=(1e-4, 1e-1)))
        gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                      n_restarts_optimizer=2, random_state=int(self.rng.integers(1e9)))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ConvergenceWarning)
            gp.fit(X, y)

        # Expected Improvement over a random candidate pool (cheap, no gradients)
        cand = self.rng.random((self.n_candidates, X.shape[1]))
        mu, sigma = gp.predict(cand, return_std=True)
        sigma = np.maximum(sigma, 1e-9)
        best = y.max()
        z = (mu - best) / sigma
        ei = (mu - best) * norm.cdf(z) + sigma * norm.pdf(z)
        ei[sigma < 1e-9] = 0.0

        # Soft feasibility penalty: down-weight candidates near known failures.
        # Acts like a simplified constrained-BO feasibility term so the optimizer
        # stops re-proposing into a region that yields no usable data.
        if failed:
            F = np.array(failed)
            # squared distance from each candidate to its nearest failure point
            d2 = ((cand[:, None, :] - F[None, :, :]) ** 2).sum(axis=2).min(axis=1)
            feasibility = 1.0 - np.exp(-d2 / (2.0 * 0.08 ** 2))  # ~0 near failures
            ei = ei * feasibility

        return self.space.from_unit(cand[int(np.argmax(ei))])
