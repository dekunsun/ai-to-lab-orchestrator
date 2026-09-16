# Architecture

How this system is put together, and — more usefully — *why*, including the
things I chose not to build.

> **One sentence:** this is not a materials simulator; it is the layer that
> connects a decision about what to try next to the evidence that it was
> actually tried, safely, with data good enough to decide on again.

---

## 1. The problem this layer exists to solve

AI models for materials propose candidates far faster than labs can evaluate
them. The bottleneck is not model accuracy — it is that a prediction does not
automatically become an experiment, an experiment does not automatically become
trustworthy data, and trustworthy data does not automatically become the next
decision. Everything in between is operational: scheduling, validation, safety
review, provenance, data quality, and deciding what is even eligible to feed
back into a model.

That "in between" is the entire subject of this repo.

---

## 2. Layers

Five concerns, deliberately separated so each can be reasoned about — and
swapped — on its own.

```
┌─ Data contracts ─────────────────────────────────────────────┐
│  workflow YAML shape, device result schema, policy schema    │
└──────────────────────────────────────────────────────────────┘
┌─ Orchestration ──────────────────────────────────────────────┐
│  workflow_parser → safety_gate → executor → step sequencing  │
└──────────────────────────────────────────────────────────────┘
┌─ Experiment data (the system's memory) ──────────────────────┐
│  SQLite: experiments, workflow_steps, artifacts              │
└──────────────────────────────────────────────────────────────┘
┌─ Decision ───────────────────────────────────────────────────┐
│  optimizer/ (what to try next) + policy/ (what "good" means) │
└──────────────────────────────────────────────────────────────┘
┌─ Governance ─────────────────────────────────────────────────┐
│  hazard rules, block/flag verdicts, data-quality gating       │
└──────────────────────────────────────────────────────────────┘
```

| Layer | Question it answers | Status |
|---|---|---|
| Data contracts | If a device changes its output shape, do we find out? | Partial — structured dicts + policy validation, no Pydantic |
| Orchestration | How does an intent become an auditable sequence of steps? | Done (synchronous) |
| Experiment data | What is the system's memory? Do failures count as data? | Partial — 3 of 8 planned tables |
| Decision | What next, and by whose definition of "good"? | Done for CdTe; hydride triage not started |
| Governance | Who approved this, and which data may train a model? | Safety gate done; hypothesis registry not started |

---

## 3. Lifecycle of one experiment

This is the path that actually executes today.

```
optimizer.suggest(history)
    │   sees only experiments that succeeded AND passed the data-quality gate
    ▼  params
safety_gate.review_parameters()
    │   ① bounds / completeness   ② hazard rules on parameter COMBINATIONS
    ├─ blocked / rejected ──► status=blocked, ZERO devices run, y=None to optimizer
    ▼  approved | approved_with_flags
executor.execute_workflow()
    │   runs the 6 steps in YAML order, threading each step's outputs downstream
    ├─ any device returns failed ──► short-circuit, failure_category recorded
    ▼
scoring_engine  ── applies the WeightedPolicy ──► objective_score
    │             records policy_id + per-term contributions
    ▼
data_quality_score ≥ 0.5 ?  ──► included_in_optimizer
    ▼
SQLite: experiments / workflow_steps / artifacts
    ▼
y fed back to optimizer ──► next proposal
```

Two details worth pausing on:

**`blocked` is not `failed`.** A failure means a sample was consumed and
produced nothing. A block means the gate refused to consume a sample at all.
They cost a real lab completely different amounts, so they are separate statuses
and the benchmark reports them separately.

**The optimizer's view of history is filtered.** It does not see every
experiment — it sees successful experiments whose data cleared a quality
threshold, plus the *locations* of failures (used for feasibility, not
regression). "What is eligible to condition the next decision" is itself a
governed question.

---

## 4. Design stances

### 4.1 Devices do not raise on scientific failure

A degraded sample is not an exception, it is a result. `devices/base.py` returns
`status="failed"` with a `failure_category`; devices only raise on genuine
programming errors. This makes failure **first-class data** — categorized,
persisted, queryable, and usable by the optimizer to avoid dead regions.

A system that throws on a bad experiment cannot learn from bad experiments, and
in materials research most experiments are bad ones.

### 4.2 Measurement is separated from objective

Six devices emit *measurements* — crystallinity, phase purity, bandgap, a J-V
curve. Only `ScoringEngine` turns measurements into a decision number.

The justification is literal: a real XRD instrument does not know your
optimization target. Keeping the objective out of the instruments means you can
change what you are optimizing for without touching any device, which is exactly
what §4.3 exploits.

### 4.3 The trade-off weights are a policy, not a constant

`policy/weighted_policy.py` loads weights from `configs/policies/*.yaml`.
Three CdTe policies ship: performance-first, balanced, manufacturability-first.

This matters more than it looks. The weights are the single most contestable
assumption in the system — they encode what the team currently values — and
burying them as literals inside a device hides them from exactly the people who
should be arguing about them. Made explicit, they become reviewable, versionable
artifacts, and the recorded `policy_id` means every score can be traced to the
priorities that produced it.

Invariants the module enforces:

- weights are non-negative and **sum to 1.0**, so scores stay comparable
  between policies (otherwise a policy could score higher just by weighing more);
- a metric named in a policy but absent from the data **raises**. A silent 0.0
  would let a typo quietly redirect every decision the system makes;
- `contributions()` exposes the per-term breakdown, so a dashboard can show
  *why* something scored as it did, not only the total.

The same mechanism is what hydride triage will use, so both halves of the
project make trade-offs the same auditable way.

### 4.4 The optimizer sits behind a swappable interface

`suggest(history) -> params` is the whole contract. Two implementations:
`RandomSearch` (honest baseline) and `BayesianOptimizer` (GP + Expected
Improvement, ~60 readable lines).

Hand-rolling the GP was a deliberate choice, not a packaging accident: the
project's purpose is to *explain* a closed loop, and a black box cannot be
explained. It also paid off directly — see §5.1. In production, Ax or Optuna
drops in behind the same interface without the orchestrator noticing.

### 4.5 Governance must be able to say no

A guardrail that only annotates is decoration. Hazard rules carry an explicit
`action`: `block` stops the experiment before any device runs; `flag` records
the risk and proceeds. Blocked proposals return `y=None` to the optimizer, so
the safety policy actively **shapes the search space** rather than commenting on
it afterwards.

The thresholds are set deliberately *wider* than the true failure region
(block at 440 °C/40 min; samples degrade at 450 °C/45 min) because a real lab
does not know exactly where the cliff is — a guardrail belongs inside the
uncertainty band, not on its edge. This costs reachable search space, which is
why `blocked` is reported as its own rate: **governance is not free, and the
system should show its price rather than hide it.**

---

## 5. Things that went wrong, and what they taught

These are real defects found in this codebase, not hypotheticals. They are the
most useful part of the document.

### 5.1 Bayesian optimization got trapped in a failure region

Failed experiments yield no objective value, so a naive GP never learns they are
bad and keeps re-proposing into the dead zone, burning budget.

Fixed with two mechanisms: a **soft feasibility penalty** that down-weights
candidates near known failures, and an **escape hatch** that forces exploration
after a streak of failures. This is a simplified constrained-BO feasibility
term, and it is a problem every autonomous lab hits.

### 5.2 The safety gate protected nothing

The original hazard rule fired at `temp > 455 AND time > 50`, while samples
degraded at `temp > 450 AND time > 45`. The hazard region was a strict *subset*
of the failure region: every experiment the gate flagged was already doomed, so
the gate prevented zero damage while appearing to work in every demo.

This is the characteristic failure mode of a governance layer — it looks
identical whether or not it functions. Fixed by widening the rule and adding
`tests/test_safety_gate.py`, which samples 20,000 random points and asserts no
degrading parameter set can reach a device.

### 5.3 The benchmark numbers were wrong and unreproducible

The README claimed a BO median of 0.84. The measured value was 0.806, and no
script in the repo produced either number. Fixed by making
`scripts/run_cdte_benchmark.py` the sole source of every published figure.

### 5.4 One RNG served both the lab and the optimizer

Both drew from a single `Generator`. BO draws ~512 candidates per iteration;
random search draws 5 — so the two methods advanced the shared stream at wildly
different rates and therefore faced **different measurement noise**. Per-seed
comparison was meaningless, and results shifted when unrelated knobs like
`n_candidates` changed.

Fixed by spawning separate streams from one seed, and re-deriving the lab stream
per experiment index so both methods meet the same noise draws at equal budget
(common random numbers).

### 5.5 Rounding to 6 decimals moved the median by 0.006

Extracting the weights into a policy object briefly rounded each weighted term
before summing — a ≤1e-4 perturbation. It changed which point the GP held as
incumbent, changed the argmax of Expected Improvement, and sent the search down
an entirely different path.

The general lesson is the valuable one: **closed-loop systems are chaotically
sensitive to their own numerics.** Differences below ~0.01 in these curves are
not real, and a champion condition needs replication before it is believed.
Round for display, never before a decision.

---

## 6. Benchmark methodology

- **Fixed budget, many seeds.** One trajectory proves nothing; what matters is
  the distribution of outcomes at equal experimental cost.
- **Median + IQR, never mean ± std.** The final-best distribution is bounded and
  skewed (there is a ceiling near 0.897), so a mean misleads.
- **Common random numbers** across methods, so per-seed comparison is valid.
- **Failure-aware accounting**: `failed` and `blocked` reported separately.
- **The ceiling line is the noise-free maximum.** Reported scores are noisy
  observations, so "best found so far" is an *optimistically biased* estimator —
  taking a max over noisy draws captures luck. Runs legitimately exceed the
  line. Any lab ranking candidates by single-shot best-observed inherits this
  bias, which is why replication is a governance concern and not a nicety.

---

## 7. What I deliberately did not build

Scope discipline is part of the argument, so the omissions are explicit.

| Not built | Why |
|---|---|
| A physically accurate CdTe simulator | Would require real process data. The surrogate is honest about being a benchmark environment; a fake physics model would be worse than none. |
| Simulated DFPT / electron-phonon / Tc for hydrides | Same reason. Phase 3 uses *published* values and builds triage on top. |
| A graphene tactile-sensor use case | No grounded response model available. Two defensible use cases beat three thin ones. |
| A real async task queue (Celery / Kafka) | The state machine concept is what matters; the infrastructure would add operational surface without strengthening the argument. Maps cleanly to a task queue in production. |
| Pydantic everywhere | Structured dicts plus validation at the boundaries that matter. Full contract enforcement is worth it in production, not at prototype scale. |

---

## 8. Known gaps

Honest current state, in rough priority order:

1. **CdTe and hydride triage are not connected.** Today they would be two
   independent modules in one repo. The intended flow — triage ranks candidates
   → validation plan generates a workflow → the same executor runs it →
   evidence updates confidence and re-ranks — is what makes this an
   *orchestrator* rather than two demos. This is the most important remaining work.
2. **Five of eight planned tables are missing**: `measurements`, `failures`,
   `safety_reviews`, `model_feedback`, `hypotheses`. Their content currently
   lives inside JSON columns, which limits what a governance view can query.
3. **No hypothesis registry.** This is the difference between "I ran
   experiments" and "I built a system that tracks hypotheses, evidence, and
   decisions" — high narrative value, low build cost.
4. **Execution is synchronous.** Fine for a benchmark; the `queued/running`
   states in the state-machine story are not yet real.
5. **No dashboard.** Nothing can currently be shown to a non-technical reviewer
   without reading code.
