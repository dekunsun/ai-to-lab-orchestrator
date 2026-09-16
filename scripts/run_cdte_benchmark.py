"""Multi-seed BO-vs-random benchmark on the CdTe surrogate.

This script is the ONLY source of the numbers quoted in the README. If a number
appears in the README, it came out of here and can be regenerated:

    python scripts/run_cdte_benchmark.py --seeds 30 --budget 30

Why it is built this way
------------------------
* Fixed experiment budget, many seeds. A single trajectory proves nothing about
  an optimizer; what matters is the distribution of outcomes at equal cost.
* Median + IQR, never mean +/- std. The final-best distribution is bounded and
  skewed (there is a ceiling near 0.90), so a mean is misleading.
* Failure-aware accounting. `failed` (a sample was consumed and yielded nothing)
  and `blocked` (the safety gate refused to spend a sample at all) are reported
  separately, because they cost a real lab very different amounts.
* Both methods draw from the same per-experiment lab noise stream
  (common random numbers) — see run_cdte_demo.run_closed_loop.
"""

from __future__ import annotations
import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from run_cdte_demo import run_closed_loop, OPTIMIZERS
from devices.cdte.devices import DEFAULT_CDTE_POLICY
from policy.weighted_policy import WeightedPolicy

OUT_DIR = "artifacts/benchmark_results"


def summarize(finals: list[float]) -> dict:
    q = statistics.quantiles(finals, n=4) if len(finals) >= 4 else [float("nan")] * 3
    return {
        "median": round(statistics.median(finals), 4),
        "q1": round(q[0], 4),
        "q3": round(q[2], 4),
        "min": round(min(finals), 4),
        "max": round(max(finals), 4),
    }


def run_benchmark(methods: list[str], seeds: int, budget: int,
                  policy: str | None = None) -> dict:
    results: dict[str, dict] = {}
    for method in methods:
        runs = []
        for seed in range(seeds):
            r = run_closed_loop(method, budget=budget, seed=seed,
                                persist=False, verbose=False, policy=policy)
            runs.append(r)
            print(f"  {method:24s} seed {seed:>2}  best={r['final_best']:.4f}  "
                  f"failed={r['n_failed']}  blocked={r['n_blocked']}", flush=True)

        finals = [r["final_best"] for r in runs]
        # median convergence curve + IQR band across seeds, per experiment index
        traj = np.array([r["best_trajectory"] for r in runs])       # (seeds, budget)
        results[method] = {
            "final_best": summarize(finals),
            "final_best_per_seed": finals,
            "curve_median": np.median(traj, axis=0).round(4).tolist(),
            "curve_q1": np.percentile(traj, 25, axis=0).round(4).tolist(),
            "curve_q3": np.percentile(traj, 75, axis=0).round(4).tolist(),
            "mean_failure_rate": round(float(np.mean([r["failure_rate"] for r in runs])), 4),
            "mean_blocked_rate": round(float(np.mean([r["blocked_rate"] for r in runs])), 4),
            "mean_valid_feedback_rate": round(
                float(np.mean([r["valid_feedback_rate"] for r in runs])), 4),
            # median operating point across seeds — different policies should
            # steer the optimizer to genuinely different process conditions
            "median_best_params": {
                k: round(float(np.median([r["best_params"][k] for r in runs
                                          if r["best_params"]])), 1)
                for k in (runs[0]["best_params"] or {})
            },
        }
    return results


def paired_comparison(results: dict, a: str, b: str) -> dict | None:
    """Per-seed win rate. Meaningful only because both methods share the same
    per-experiment lab noise stream at each seed."""
    if a not in results or b not in results:
        return None
    fa, fb = results[a]["final_best_per_seed"], results[b]["final_best_per_seed"]
    wins = sum(1 for x, y in zip(fa, fb) if x > y)
    return {"a": a, "b": b, "a_wins": wins, "n": len(fa),
            "median_gap": round(statistics.median(fa) - statistics.median(fb), 4)}


def markdown_table(results: dict, budget: int) -> str:
    lines = [
        f"| Method | Median best @ {budget} exp | IQR | Failure rate | Blocked by gate | Valid feedback |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for m, r in results.items():
        s = r["final_best"]
        lines.append(
            f"| {m} | **{s['median']:.3f}** | [{s['q1']:.3f}, {s['q3']:.3f}] | "
            f"{r['mean_failure_rate']:.0%} | {r['mean_blocked_rate']:.0%} | "
            f"{r['mean_valid_feedback_rate']:.0%} |")
    return "\n".join(lines)


def plot(results: dict, budget: int, seeds: int, path: str) -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (matplotlib not installed — skipping chart)")
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5),
                                   gridspec_kw={"width_ratios": [2, 1]})
    x = np.arange(1, budget + 1)
    colors = {"bayesian_optimization": "#1f77b4", "random_search": "#8c8c8c"}
    for m, r in results.items():
        c = colors.get(m, None)
        ax1.plot(x, r["curve_median"], label=f"{m} (median)", color=c, lw=2)
        ax1.fill_between(x, r["curve_q1"], r["curve_q3"], alpha=0.18, color=c)
    ax1.axhline(0.897, ls="--", lw=1, color="#444",
                label="surrogate ceiling ~0.897")
    ax1.set_xlabel("experiments run (fixed budget)")
    ax1.set_ylabel("best objective found so far")
    ax1.set_title(f"CdTe closed loop: convergence ({seeds} seeds, median + IQR)")
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(alpha=0.25)

    box_data = [r["final_best_per_seed"] for r in results.values()]
    box_labels = [m.replace("_", "\n") for m in results]
    try:  # matplotlib >= 3.9 renamed `labels` to `tick_labels`
        ax2.boxplot(box_data, tick_labels=box_labels, widths=0.5)
    except TypeError:
        ax2.boxplot(box_data, labels=box_labels, widths=0.5)
    ax2.axhline(0.897, ls="--", lw=1, color="#444")
    ax2.set_ylabel(f"final best after {budget} experiments")
    ax2.set_title("Final-best distribution")
    ax2.grid(alpha=0.25, axis="y")

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--budget", type=int, default=30)
    ap.add_argument("--methods", default=",".join(OPTIMIZERS))
    ap.add_argument("--policy", default=None,
                    help=f"scoring policy YAML (default: {DEFAULT_CDTE_POLICY})")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args()

    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    os.makedirs(args.out, exist_ok=True)

    pol = WeightedPolicy.from_yaml(args.policy or DEFAULT_CDTE_POLICY)
    print(f"\nCdTe benchmark | {args.seeds} seeds x {args.budget} experiments | "
          f"methods: {', '.join(methods)}\n"
          f"Scoring policy: {pol.name} ({pol.policy_id})\n")
    results = run_benchmark(methods, args.seeds, args.budget, policy=args.policy)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seeds": args.seeds,
        "budget": args.budget,
        "surrogate_ceiling": 0.897,
        "policy": pol.provenance(),
        "results": results,
        "paired": paired_comparison(results, "bayesian_optimization", "random_search"),
    }
    suffix = "" if pol.policy_id == "cdte_balanced_device_quality" else f"_{pol.policy_id}"
    json_path = os.path.join(args.out, f"cdte_benchmark{suffix}.json")
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2)

    table = markdown_table(results, args.budget)
    md_path = os.path.join(args.out, f"cdte_benchmark{suffix}.md")
    with open(md_path, "w") as f:
        f.write(f"# CdTe benchmark ({args.seeds} seeds, budget {args.budget})\n\n"
                f"Scoring policy: **{pol.name}** (`{pol.policy_id}`), "
                f"weights `{pol.weights}`\n\n"
                f"Generated {payload['generated_at']} by "
                f"`scripts/run_cdte_benchmark.py`\n\n{table}\n")

    chart = plot(results, args.budget, args.seeds,
                 os.path.join(args.out, f"cdte_convergence{suffix}.png"))

    print("\n" + table)
    if payload["paired"]:
        p = payload["paired"]
        print(f"\nPaired per-seed: BO beat random on {p['a_wins']}/{p['n']} seeds "
              f"(median gap {p['median_gap']:+.3f})")
    print(f"\nwrote {json_path}\n      {md_path}" + (f"\n      {chart}" if chart else "") + "\n")


if __name__ == "__main__":
    main()
