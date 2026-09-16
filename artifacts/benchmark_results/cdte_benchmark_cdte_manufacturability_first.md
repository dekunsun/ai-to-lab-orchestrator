# CdTe benchmark (30 seeds, budget 30)

Scoring policy: **Manufacturability first** (`cdte_manufacturability_first`), weights `{'crystallinity_score': 0.3, 'phase_purity': 0.3, 'defect_passivation_score': 0.25, 'pce_proxy': 0.15}`

Generated 2026-09-16T15:46:09+00:00 by `scripts/run_cdte_benchmark.py`

| Method | Median best @ 30 exp | IQR | Failure rate | Blocked by gate | Valid feedback |
|---|---:|---|---:|---:|---:|
| bayesian_optimization | **0.926** | [0.898, 0.945] | 12% | 5% | 83% |
