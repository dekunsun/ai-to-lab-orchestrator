# AI-to-Lab Orchestrator for Materials Discovery

A working prototype of the operating layer for a self-driving materials lab: it
turns an optimizer's proposed experiment into an executed, logged workflow,
feeds the result back to close the loop, and supports transparent decision-making
over real published data.

Built to demonstrate hands-on understanding of the closed-loop, data, and
decision internals of lab-in-the-loop research.

## Scope

An orchestration and decision-support prototype, not a materials simulator.

- The **CdTe** use case runs on a literature-inspired surrogate environment —
  observation noise, a non-smooth process window, an over-treatment cliff, and
  experiment failures — designed to benchmark closed-loop optimization under
  realistic difficulty.
- The **Hydride** use case is built on real published data (25 superconductors
  from a GNoME screening paper); ranking and decision support sit on top of the
  published Tc / lambda / omega_log values directly.

The judgment on display is knowing where a surrogate is appropriate and where
real data is required.

## Two use cases

| | CdTe | Hydrides |
|---|---|---|
| Type | Closed-loop process optimization | Decision-support triage |
| Data | Literature-inspired surrogate | Published experimental data |
| Shows | Closed-loop execution + rigorous benchmarking | Transparent, data-grounded decisions |

## Use case 1 — CdTe closed-loop optimization

An optimizer proposes process parameters; a pipeline of virtual instruments runs
the experiment (with noise and possible failure); the score feeds back; repeat.

Bayesian optimization is benchmarked against random search across 30 seeds under
a fixed experiment budget, reporting **median + IQR across seeds**, since single
runs vary widely. BO reaches a median best of ~0.78 (near the surrogate's
optimum) vs ~0.66 for random, with a tighter spread — higher *and* more reliable.

![Benchmark: BO vs random convergence, median ± IQR over 30 seeds](artifacts/benchmark_convergence.png)

## Use case 2 — Hydride candidate triage

Ranks 25 published hydride superconductors for experimental validation. Ranking
weights are **decision policies, not fixed constants**: under a `max_tc` policy
the highest-Tc material (LiZrH6Ru, 23.5 K) ranks first; under a
`lab_feasible_first` policy it drops out of the top 5, reflecting the paper's
insight that extreme Tc correlates with thermodynamic instability. Every
Tc / lambda / omega_log value is taken directly from the paper; the system adds
ranking, trade-off analysis, and a data-grounded validation plan on top.

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# CdTe: one closed-loop run
python3 run_loop.py

# CdTe: BO vs random benchmark across 30 seeds
python3 benchmark.py

# CdTe: generate the convergence chart
python3 plot_benchmark.py

# Hydrides: triage + validation plans
python3 run_triage.py
```

## Architecture

```
landscape   -> the surrogate "truth" (CdTe)
devices     -> virtual instruments (measure truth + add noise + can fail)
executor    -> runs devices in order, threads data downstream, stops on failure
optimizer   -> pluggable interface; random search + GP/Expected-Improvement BO
run_loop    -> the closed loop
benchmark   -> many-seed median + IQR comparison
triage      -> hydride decision support over real published data
```

## Notable engineering decisions

See `docs/decision_log.md` for the real trade-offs made while building this —
including diagnosing a GP convergence failure caused by unnormalized parameter
scales, fixing a Bayesian optimizer that got stuck in experiment-failure regions,
and finding that single-run results vary widely (hence the seed-based benchmark).