"""Plot the chart: BO vs random convergence, median + IQR band."""

import matplotlib
matplotlib.use("Agg")   # save to file, don't try to open a window
import matplotlib.pyplot as plt

from benchmark import benchmark


def plot(n_seeds=30, budget=30, out="artifacts/benchmark_convergence.png"):
    print("Running benchmark for the plot (~30s)...")
    res = benchmark(n_seeds=n_seeds, budget=budget)

    x = range(1, budget + 1)   # experiment numbers 1..budget

    styles = {
        "bayesian_optimization": ("Bayesian optimization", "#2b6cb0"),
        "random_search": ("Random search", "#a0aec0"),
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    for method, (label, color) in styles.items():
        r = res[method]
        ax.plot(x, r["traj_median"], color=color, linewidth=2.2, label=label)
        ax.fill_between(x, r["traj_q25"], r["traj_q75"], color=color, alpha=0.18)

    ax.set_xlabel("Experiments run")
    ax.set_ylabel("Best objective found so far")
    ax.set_title(f"Closed-loop sample efficiency (median \u00b1 IQR over {n_seeds} seeds)")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.25)
    ax.set_ylim(0, 1)

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"saved {out}")


if __name__ == "__main__":
    plot()
