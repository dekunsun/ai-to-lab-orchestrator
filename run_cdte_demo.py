"""Phase 1 demo: one closed-loop CdTe optimization run.

    YAML -> safety gate -> executor -> noisy CdTe surrogate
         -> SQLite -> optimizer feedback -> next experiment -> repeat

Run:  python run_cdte_demo.py --budget 30 --seed 0
Prints the best-objective-so-far trajectory and persists every experiment.

For the multi-seed BO-vs-random comparison, use scripts/run_cdte_benchmark.py.
"""

from __future__ import annotations
import argparse
import numpy as np

from orchestrator.workflow_parser import load_workflow
from orchestrator.executor import execute_workflow
from devices.cdte.devices import build_cdte_devices, DEFAULT_CDTE_POLICY
from optimizer.optimizers import BayesianOptimizer, RandomSearch, _ParamSpace
from policy.weighted_policy import WeightedPolicy
from db import store

WORKFLOW_PATH = "configs/workflows/cdte_thin_film_solar_optimization.yaml"

OPTIMIZERS = {
    "bayesian_optimization": BayesianOptimizer,
    "random_search": RandomSearch,
}


def run_closed_loop(method_name: str, budget: int, seed: int,
                    persist: bool = True, verbose: bool = True,
                    policy: str | None = None) -> dict:
    """Run one closed loop and return its trajectory + failure-aware metrics.

    Randomness design (this matters for the benchmark being honest):

    The lab and the optimizer draw from SEPARATE streams, spawned from one seed.
    Previously both shared a single Generator, which meant BO — drawing ~512
    candidate points per iteration — advanced the stream far faster than random
    search, so the two methods faced *different* measurement noise. That made
    per-seed comparison meaningless and made results sensitive to unrelated
    knobs like `n_candidates`.

    Beyond separating them, the lab stream is re-derived per experiment index,
    so experiment #7 under BO and experiment #7 under random search draw the
    SAME noise values. This is the common-random-numbers variance reduction
    trick: it does not make the methods see identical measurements (they
    evaluate different parameters), but it removes noise-draw luck as a source
    of difference between methods at equal budget.
    """
    lab_ss, opt_ss = np.random.SeedSequence(seed).spawn(2)
    lab_seeds = lab_ss.spawn(budget)
    opt_rng = np.random.default_rng(opt_ss)

    scoring_policy = WeightedPolicy.from_yaml(policy or DEFAULT_CDTE_POLICY)

    workflow = load_workflow(WORKFLOW_PATH)
    bounds = workflow.param_bounds()
    space = _ParamSpace(bounds)

    try:
        opt = OPTIMIZERS[method_name](bounds, opt_rng)
    except KeyError:
        raise ValueError(f"unknown method: {method_name}") from None

    conn = store.connect() if persist else None

    history: list[dict] = []          # what the optimizer sees (x_unit + y)
    best_trajectory: list[float] = []
    best_so_far = 0.0
    n_failed = n_blocked = 0

    for i in range(budget):
        params = opt.suggest(history)
        devices = build_cdte_devices(np.random.default_rng(lab_seeds[i]), scoring_policy)
        record = execute_workflow(workflow, devices, params)

        y = record["objective_score"] if record["included_in_optimizer"] else None
        history.append({"x_unit": space.to_unit(params), "y": y,
                        "params": params, "status": record["status"]})

        if y is not None:
            best_so_far = max(best_so_far, y)
        elif record["status"] == "blocked":
            n_blocked += 1
        else:
            n_failed += 1
        best_trajectory.append(round(best_so_far, 4))

        if persist:
            store.save_experiment(conn, record, method=method_name, run_seed=seed)

        if verbose:
            if y is not None:
                outcome = f"{y:.4f}"
            elif record["status"] == "blocked":
                outcome = f"BLOCKED({record['failure_category']})"
            else:
                outcome = f"FAILED({record['failure_category']})"
            print(f"  exp {i+1:>2}/{budget}  score={outcome:>34}  best={best_so_far:.4f}")

    if conn:
        conn.close()

    n_valid = budget - n_failed - n_blocked
    best_idx = max(
        (h for h in history if h["y"] is not None), key=lambda h: h["y"], default=None)

    return {
        "method": method_name,
        "seed": seed,
        "policy_id": scoring_policy.policy_id,
        "best_params": {k: round(v, 2) for k, v in best_idx["params"].items()} if best_idx else None,
        "budget": budget,
        "best_trajectory": best_trajectory,
        "final_best": best_so_far,
        "n_failed": n_failed,
        "n_blocked": n_blocked,
        "n_valid": n_valid,
        "failure_rate": n_failed / budget,
        "blocked_rate": n_blocked / budget,
        "valid_feedback_rate": n_valid / budget,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="bayesian_optimization", choices=list(OPTIMIZERS))
    ap.add_argument("--budget", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--policy", default=None,
                    help=f"path to a scoring policy YAML (default: {DEFAULT_CDTE_POLICY})")
    ap.add_argument("--no-persist", action="store_true",
                    help="skip writing to db/lab.sqlite")
    args = ap.parse_args()

    pol = WeightedPolicy.from_yaml(args.policy or DEFAULT_CDTE_POLICY)
    print(f"\nClosed-loop CdTe optimization  |  method={args.method}  "
          f"budget={args.budget}  seed={args.seed}\n"
          f"Scoring policy: {pol.name} ({pol.policy_id})  weights={pol.weights}\n")
    r = run_closed_loop(args.method, args.budget, args.seed,
                        persist=not args.no_persist, policy=args.policy)
    print(f"\nFinal best objective: {r['final_best']:.4f}"
          f"   failed: {r['n_failed']}/{r['budget']}"
          f"   blocked by safety gate: {r['n_blocked']}/{r['budget']}"
          f"   valid feedback: {r['valid_feedback_rate']:.0%}")
    print(f"Best conditions found: {r['best_params']}\n")


if __name__ == "__main__":
    main()
