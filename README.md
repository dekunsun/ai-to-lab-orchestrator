# AI-to-Lab Orchestrator for Materials Discovery

A focused self-driving-lab prototype: it turns an AI/optimizer's *next-experiment*
suggestion into an executable workflow, runs it on virtual lab devices, captures
structured + provenance-rich data, handles failures and safety review, and feeds
clean results back to close the loop.

> This repo is a **systems / orchestration** portfolio, not a physics simulator.
> See "Scientific modeling scope" below.

---

## Status: Phase 1 complete + benchmark hardened

The full closed loop runs end-to-end:

```
YAML workflow → safety gate → executor → noisy CdTe surrogate devices
            → SQLite logging → optimizer feedback → next experiment → repeat
```

### Setup

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

### Run one closed loop

```bash
./.venv/bin/python run_cdte_demo.py --method bayesian_optimization --budget 30 --seed 0
```

Every experiment (parameters, per-step outputs, artifacts, failures, safety
review, data-quality, model-feedback eligibility) is persisted to `db/lab.sqlite`.

### Reproduce the benchmark

```bash
./.venv/bin/python scripts/run_cdte_benchmark.py --seeds 30 --budget 30
./.venv/bin/python -m pytest tests/ -q          # 47 tests
```

---

## Benchmark results

**Every number below is produced by `scripts/run_cdte_benchmark.py`** and written
to `artifacts/benchmark_results/`. Nothing here is hand-entered.

30 seeds × 30-experiment budget:

| Method | Median best @ 30 exp | IQR | Failure rate | Blocked by gate | Valid feedback |
|---|---:|---|---:|---:|---:|
| Bayesian optimization | **0.818** | [0.723, 0.855] | 11% | 4% | 85% |
| Random search | **0.724** | [0.663, 0.806] | 12% | 7% | 81% |

Paired per-seed: BO beat random on **20/30 seeds**, median gap **+0.093**.

![convergence](artifacts/benchmark_results/cdte_convergence.png)

**How to read this honestly** — three things I want a reviewer to notice:

1. **The IQR bands overlap.** BO wins in the median and wins most seeds, but it
   does not dominate. On a 5-dimensional landscape with a 30-experiment budget
   that is the expected result, and a chart showing clean separation would be a
   sign the benchmark was too easy.
2. **BO does not pull ahead until roughly experiment 10.** Before that it is
   running its initial design, so it is *behind* random early. The advantage is
   sample efficiency later in the budget, not from the first experiment.
3. **A few runs exceed the 0.897 ceiling line.** That is not a bug. The dashed
   line is the maximum of the noise-free landscape; the reported score is a
   *noisy observation*, so "best found so far" is an optimistically biased
   estimator — taking a max over noisy draws is luck-prone by construction. Any
   self-driving lab that ranks candidates by single-shot best-observed has this
   bias, which is why replication matters before believing a champion.

---

## Decision policies: the weights are configurable, not constants

The objective is not baked into a simulated instrument. `ScoringEngine` collapses
measurements into one number using a **weighted policy** loaded from
`configs/policies/`, because "how much is phase purity worth relative to
efficiency?" is a research-strategy question, not a property of an XRD machine.

```bash
./.venv/bin/python run_cdte_demo.py --policy configs/policies/cdte_manufacturability_first.yaml
```

Same closed loop, same surrogate, same BO — 30 seeds, only the policy differs:

| Policy | Median best | Median treatment time found | Median dopant |
|---|---:|---:|---:|
| Performance first | 0.773 | 35.9 min | 1.2 % |
| Balanced device quality *(default)* | 0.818 | 40.0 min | 1.3 % |
| Manufacturability first | 0.926 | **27.7 min** | **0.9 %** |

**The headline scores are not comparable across rows** — each policy defines a
different objective, so a higher number does not mean a better process. That is
the point, and stating it is part of the demo. The comparable quantity is the
*operating point*: manufacturability-first converges on a treatment ~12 minutes
shorter and lighter doping, i.e. a visibly more conservative process that sits
further from the over-treatment interaction penalty. Treatment temperature lands
near 388 °C under every policy, because that window dominates the landscape —
policy influences the parameters the objective leaves room to argue about.

Every experiment records which policy scored it (`experiments.policy_id`), and
the per-term contributions are kept in the step metadata, so any score can be
decomposed into *why*. The same `WeightedPolicy` mechanism is what Phase 3's
hydride triage will use, so both halves of the system make trade-offs the same
auditable way.

---

## Hydride candidate triage: published data, explicit judgment

The second use case ranks 22 ambient-pressure hydride superconductor candidates
and turns the winner into an executable validation plan.

```bash
./.venv/bin/python scripts/run_hydride_triage.py
./.venv/bin/python scripts/run_hydride_triage.py --policy configs/policies/hydride_lab_feasible_first.yaml
```

**No physics is simulated here.** `datasets/hydrides/gnome_hydride_candidates.csv`
is a verbatim transcription of Tables 1 and 2 of [Sanna et al., *Communications
Physics* (2026)](https://www.nature.com/articles/s42005-026-02552-4) — λ, ω_log
and Allen–Dynes Tc for 18 vacancy-ordered double perovskites and 4 fluorite-like
hydrides. Provenance is enforced as a *file* boundary, and a test fails if it
erodes:

| Tier | Where it lives | Example |
|---|---|---|
| **Published** | `datasets/hydrides/` | λ = 1.00, ω_log = 341.59 K, Tc_AD = 23.5 K |
| **Derived** | `triage/derive.py` | Tc confidence, from coupling regime + refinement status |
| **Analyst judgment** | `configs/triage/element_feasibility.yaml` | synthesis feasibility, from elemental constraints |

The paper published no score, weight, confidence or feasibility value, so none
is presented as though it had. Full detail in [datasets/hydrides/SOURCE.md](datasets/hydrides/SOURCE.md).

### What the triage actually surfaces

| Candidate | Balanced | High-Tc | Lab-feasible | Verdict |
|---|---:|---:|---:|---|
| LiZrH₆Ru | 1 | 1 | 1 | stable — leads under every policy |
| Ta₆MoH₁₆ | 2 | 3 | 2 | stable |
| TaNb₃H₈ | 3 | 4 | 3 | stable |
| EuCdH₆Ru | 6 | **2** | **9** | policy-driven |
| EuLuTcH₆ | 13 | **5** | 14 | policy-driven |

Three findings the ranking exists to produce:

1. **Ten of the 22 candidates contain technetium**, which has no stable isotope.
   That is a hard constraint on the whole cohort, visible from the formula alone
   and invisible in any Tc-ordered list. Feasibility is combined as a *minimum*,
   not a mean — one disqualifying element is not offset by three convenient ones.
2. **Only one candidate has been refined beyond Allen–Dynes.** For LiZrH₆Ru the
   careful treatment moved 23.5 K → 17 K, which the authors call "an uncommon
   deviation". The other 21 rankings rest on a number the paper's own authors
   caution against over-reading, so confidence is weighted separately from Tc.
3. **The consensus shortlist is the useful output**, not rank 1. LiZrH₆Ru,
   Ta₆MoH₁₆ and TaNb₃H₈ sit in the top five under *every* policy — they are what
   you validate regardless of whose priorities win the argument. EuCdH₆Ru moving
   2 → 9 is the honest warning label on the rest.

### Triage is an entry point into the loop, not a separate module

The selected candidate becomes a workflow that goes through the **same** parser
and the **same** safety gate as a CdTe experiment, with no orchestrator changes:

```
ranked shortlist → validation plan (generated YAML) → orchestrator.workflow_parser
                 → safety_gate → hypothesis registered in db/lab.sqlite
```

The generated hydride workflow declares its own hazard rules, and the CdTe gate
blocks them correctly on first sight — 750 °C with 150 bar H₂ is refused as
`hydrogen_pressure_at_temperature`, though both values are individually in
bounds. `tests/test_hydride_triage.py` guards this; if it ever fails, the
project has gone back to being two demos in one repository.

The plan stops at `awaiting_device_implementation`. There are no hydride
synthesis devices here and none will be fabricated — that seam is where a real
lab's seam is.

---

## Architecture (4 layers)

1. **Orchestration** — `orchestrator/`: YAML parser, safety gate, executor.
2. **Data** — `db/`: SQLite store (experiments / steps / artifacts).
3. **Decision** — `optimizer/`: transparent GP + Expected-Improvement BO, random
   baseline, soft failure-avoidance + an escape hatch for infeasible regions.
   `policy/`: configurable weighted objectives. `triage/`: hydride candidate
   ranking, sensitivity analysis and validation-plan generation.
4. **Devices** — `devices/cdte/`: surrogate landscape + 6 virtual instruments.

Full design rationale, including the trade-offs I chose *against*, is in
[docs/architecture.md](docs/architecture.md).

The CdTe surrogate (`devices/cdte/landscape.py`) intentionally includes real
experimental messiness: a **narrow non-smooth CdCl₂ treatment window**, an
**over-treatment cliff**, **parameter interactions**, **observation noise**, and
**outright failures** (degraded samples, un-crystallized films). This is what
makes the optimizer comparison credible.

---

## Notable engineering details (interview material)

**BO getting trapped in failure regions.** Failed experiments yield no objective
value, so a naive GP never learns to avoid them and keeps re-proposing into the
dead zone. Fixed with (1) a soft feasibility penalty that down-weights
candidates near known failures, and (2) an escape hatch that forces exploration
after a streak of failures. This mirrors a real constrained-optimization problem
in autonomous labs.

**The safety gate has to be able to say no.** The gate's hazard rules are set
*wider* than the surrogate's true degradation region (blocks at 440 °C/40 min;
samples actually degrade at 450 °C/45 min), because a real lab does not know
exactly where the cliff is. This costs the optimizer reachable search space —
governance is not free, and the benchmark reports `blocked` separately from
`failed` so that cost is visible. A blocked experiment runs **zero** devices:
a failure burns a sample, a block prevents one from being burned.
`tests/test_safety_gate.py` asserts no degrading parameter set can slip past.

**A 1e-4 rounding change moved the benchmark median by 0.006.** While extracting
the scoring weights into a policy object I briefly rounded each weighted term to
6 decimal places before summing. Numerically irrelevant — but it changed which
point the GP held as incumbent, which changed the argmax of Expected
Improvement, and sent the entire search down a different path. Fixed by never
rounding before a decision (`tests/test_scoring_policy.py` guards it). The
lesson I'd carry into a real lab: closed-loop systems have chaotic sensitivity
to their own numerics, so differences below ~0.01 in these curves should not be
treated as real, and any "champion" condition needs replication before belief.

**Fair randomness between methods.** The lab's measurement noise and the
optimizer's proposals draw from **separate** streams spawned from one seed, and
the lab stream is re-derived per experiment index so both methods meet the same
noise draws at equal budget (common random numbers). Sharing one generator —
where BO's ~512 candidate draws per iteration advance the stream far faster than
random search's 5 — would make per-seed comparison meaningless.

---

## Scientific modeling scope

This project is **not** a physically accurate simulator of CdTe solar cells.
The CdTe module is a literature-*inspired* noisy surrogate **benchmark
environment** used to test orchestration, metadata capture, failure handling,
and closed-loop optimization. It makes no claim about true PCE prediction.

The hydride module does not simulate DFPT, electron–phonon coupling or Tc at
all. It uses published values as input and builds triage, decision policy and
validation planning on top of them.

---

## Roadmap

- [x] **Phase 1** — closed loop: YAML → executor → surrogate → SQLite → BO
- [x] **Phase 2** — robust benchmark: 30 seeds, BO vs random, median/IQR curves,
      failure-aware metrics, reproducible from a script
- [x] **Phase 2.5** — decision policies extracted from code into `configs/policies/`
- [x] **Phase 3** — hydride triage from published paper data, wired into the loop
- [ ] **Phase 4** — governance: data-quality view, failure taxonomy (hypothesis
      registry landed with Phase 3)
- [ ] **Phase 5** — dashboard, deck, demo video; optional LLM-to-YAML
