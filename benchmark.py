"""Benchmark: run BO and random search across many seeds, compare medians.

A single run is dominated by luck. Running many seeds and comparing the MEDIAN
reveals the true difference between methods. This is what answers questions like
'did my failure-penalty change actually help?'
"""

import numpy as np
from run_loop import run_loop


def benchmark(n_seeds=30, budget=30):
    results = {}

    for method in ["bayesian_optimization", "random_search"]:
        finals = []         # final_best from each seed
        failures = []       # n_failed from each seed
        trajectories = []   # best-so-far curve from each seed

        for seed in range(n_seeds):
            # run quietly (verbose=False) so we don't print 30x30 lines
            r = run_loop(budget=budget, seed=seed,
                         optimizer_name=method, verbose=False)
            finals.append(r["final_best"])
            failures.append(r["n_failed"])
            trajectories.append(r["best_trajectory"])

        finals = np.array(finals)
        # trajectories is a list of 30 curves; stack into a 30 x budget array
        traj = np.array(trajectories)
        results[method] = {
            "median": float(np.median(finals)),
            "q25": float(np.percentile(finals, 25)),
            "q75": float(np.percentile(finals, 75)),
            "median_failures": float(np.median(failures)),
            # per-experiment statistics across seeds (for plotting)
            "traj_median": np.median(traj, axis=0),
            "traj_q25": np.percentile(traj, 25, axis=0),
            "traj_q75": np.percentile(traj, 75, axis=0),
        }

    return results


if __name__ == "__main__":
    print("Running benchmark (this takes ~30s)...\n")
    res = benchmark(n_seeds=30, budget=30)

    print(f"{'method':<26}{'median best':>13}{'IQR (25-75%)':>20}{'median fails':>15}")
    print("-" * 74)
    for method, r in res.items():
        iqr = f"{r['q25']:.3f} - {r['q75']:.3f}"
        print(f"{method:<26}{r['median']:>13.4f}{iqr:>20}{r['median_failures']:>15.0f}")