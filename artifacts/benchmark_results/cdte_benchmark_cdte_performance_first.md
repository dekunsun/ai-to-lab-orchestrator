# CdTe benchmark (30 seeds, budget 30)

Scoring policy: **Performance first** (`cdte_performance_first`), weights `{'pce_proxy': 0.7, 'crystallinity_score': 0.1, 'defect_passivation_score': 0.1, 'phase_purity': 0.1}`

Generated 2026-09-16T15:45:57+00:00 by `scripts/run_cdte_benchmark.py`

| Method | Median best @ 30 exp | IQR | Failure rate | Blocked by gate | Valid feedback |
|---|---:|---|---:|---:|---:|
| bayesian_optimization | **0.773** | [0.735, 0.805] | 11% | 5% | 84% |
