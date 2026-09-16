# CdTe benchmark (30 seeds, budget 30)

Scoring policy: **Balanced device quality** (`cdte_balanced_device_quality`), weights `{'pce_proxy': 0.45, 'crystallinity_score': 0.2, 'defect_passivation_score': 0.2, 'phase_purity': 0.15}`

Generated 2026-09-16T15:46:42+00:00 by `scripts/run_cdte_benchmark.py`

| Method | Median best @ 30 exp | IQR | Failure rate | Blocked by gate | Valid feedback |
|---|---:|---|---:|---:|---:|
| bayesian_optimization | **0.818** | [0.723, 0.855] | 11% | 4% | 85% |
| random_search | **0.724** | [0.663, 0.806] | 12% | 7% | 81% |
