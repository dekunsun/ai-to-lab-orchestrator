"""The closed loop: optimizer proposes -> executor runs -> result feeds back.

This is the heart of the whole system. Run it and watch 'best' climb.
"""

import numpy as np
import yaml

from devices.cdte.devices import build_cdte_devices
from orchestrator.executor import execute_workflow
from optimizer.optimizers import RandomSearch, BayesianOptimizer


def run_loop(budget=20, seed=0, optimizer_name="bayesian_optimization", verbose=True):    # --- setup ---
    with open('configs/workflows/cdte.yaml') as f:
        workflow = yaml.safe_load(f)
    rng = np.random.default_rng(seed)
    devices = build_cdte_devices(rng)

    # Build the parameter bounds dict from the workflow YAML.
    bounds = {name: (spec['min'], spec['max'])
              for name, spec in workflow['parameters'].items()}

    if optimizer_name == "bayesian_optimization":
        optimizer = BayesianOptimizer(bounds, rng)
    elif optimizer_name == "random_search":
        optimizer = RandomSearch(bounds, rng)
    else:
        raise ValueError(f"unknown optimizer: {optimizer_name}")

    # --- the closed loop ---
    history = []
    best_so_far = 0.0
    best_trajectory = []   # best-so-far after each experiment

    for i in range(budget):
        # 1. optimizer proposes parameters
        params = optimizer.suggest(history)

        # 2. executor runs the experiment
        result = execute_workflow(workflow, devices, params)
        score = result['objective_score']

        # 3. record it in history (so the optimizer could learn from it)
        history.append({'params': params, 'score': score, 'status': result['status']})

        # 4. update best-so-far (skip failed experiments, which have no score)
        if score is not None:
            best_so_far = max(best_so_far, score)
        best_trajectory.append(best_so_far)   # record best after this experiment
            

        # 5. print progress (only when verbose)
        if verbose:
            score_str = f"{score:.4f}" if score is not None else f"FAILED ({result['failure_category']})"
            print(f"  exp {i+1:>2}/{budget}   score={score_str:>20}   best={best_so_far:.4f}")

    if verbose:
        print(f"\nFinal best after {budget} experiments: {best_so_far:.4f}")

    # count how many experiments failed
    n_failed = sum(1 for h in history if h['score'] is None)
    return {"final_best": best_so_far, "n_failed": n_failed,
            "best_trajectory": best_trajectory}
if __name__ == "__main__":
    run_loop(budget=30, seed=1)