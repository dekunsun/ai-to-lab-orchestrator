# Data sources and research-to-product notes

This project is part of a broader exercise in translating recent materials
science research into product-oriented project ideas. For each paper or research
direction, I focus on three questions:

1. What did the research make possible?
2. What remains difficult to operationalize?
3. What kind of product, workflow, or system could help bridge that gap?

The goal is not only to cite the underlying research, but to show how a
product-oriented builder might turn a frontier research result into a concrete
tool, workflow, or validation system.

---

## Hydride superconductor data

### Source

Sanna, A., Cerqueira, T. F. T., Cubuk, E. D., Errea, I. & Fang, Y.-W.,
*Search for thermodynamically stable ambient-pressure superconducting hydrides
in the GNoME database*, **Communications Physics** (2026).
https://www.nature.com/articles/s42005-026-02552-4

### What the paper provides

Tables 1 and 2 report the electron-phonon coupling constant λ, the logarithmic
average phonon frequency ω_log, and the Allen-Dynes Tc for every candidate whose
Allen-Dynes Tc exceeds 4.2 K — **18 vacancy-ordered double perovskites and 4
fluorite-like hydrides, 22 in total.** `datasets/hydrides/gnome_hydride_candidates.csv`
is a verbatim transcription of exactly those rows and nothing else.

The paper publishes **no** score, confidence, feasibility or ranking. Everything
the triage layer needs beyond λ, ω_log and Tc is computed from documented rules
and kept in separate files — see
[datasets/hydrides/SOURCE.md](../datasets/hydrides/SOURCE.md) for the boundary
and [architecture.md §4.4](architecture.md) for why it is enforced as a file
boundary rather than a convention.

> **Correction, recorded deliberately.** An earlier version of this project
> shipped a hydride dataset of 25 rows whose header claimed the values were
> "taken directly from the published paper". Three of those compounds —
> YbCeTcH6, LiTiH6Ru and Ta3VH8 — do not appear anywhere in the paper: not in
> Tables 1 or 2, not in the body text. Their λ, ω_log and Tc values were
> fabricated and presented as published data. The file also carried a
> `tc_predicted` column with no stated source.
>
> This was found by fetching the paper's HTML and parsing the tables directly,
> after two passes of a summarizing tool returned three different row counts for
> the same page. The lesson generalizes past this project: **do not let a
> summarizer count things you intend to publish as fact.** It is also the single
> best argument for the provenance discipline the current version enforces.

### Product translation

The paper screens a large computational database for promising ambient-pressure
superconductors and identifies candidates such as LiZrH6Ru, which has the highest
reported Tc among them.

From a product perspective, the key insight is that a ranked list of predicted
materials is only the beginning of the discovery workflow. A lab still needs to
decide which candidates are worth validating first, based on synthesizability,
stability, cost, experimental risk, and policy constraints.

That is the opportunity this project's triage use case is built around: turn
computational screening output into a prioritized validation plan that can
support lab decision-making — and then let the resulting evidence change the
ranking that proposed the experiment.

---

## CdTe surrogate environment

### Source

This environment is literature-inspired rather than based on a single dataset.
It uses an abstract response surface whose qualitative behaviour reflects
well-known CdTe thin-film process patterns: an optimal CdCl₂ treatment window,
performance degradation from over-processing, and sensitivity to substrate
temperature.

### Reference point

First Solar's Series 7 represents a state-of-the-art commercial CdTe module line.
Its public datasheets show that CdTe is a mature technology with tightly
controlled manufacturing processes. The surrogate is deliberately a **benchmark
environment**, not a predictor of commercial efficiency — see the scientific
modeling scope note in the [README](../README.md).

### Product translation

CdTe manufacturing shows why materials optimization is not only a prediction
problem. Real process landscapes are noisy, costly to sample, and contain failure
regions. A useful system has to explore efficiently, learn from limited
experiments, and avoid spending lab capacity on low-value trials.

That is the opportunity the closed-loop benchmark is built around: test whether a
system can propose better experiments over time under realistic process
difficulty — and report honestly what that costs, including what the safety gate
refuses to spend.

---

## Background context

GNoME, released by Google DeepMind in 2023, predicted around 2.2 million stable
crystals, greatly expanding the known materials search space. Its key limitation
is that prediction alone does not complete experimental validation.

This prediction-to-validation gap is the strategic backdrop for lab-in-the-loop
and self-driving-lab systems. It is also the conceptual origin of this project.

### One-line framing

> GNoME expanded the search space to around 2.2 million predicted stable
> crystals. The next bottleneck is experimental validation. An AI-to-lab
> orchestrator is one way to help close that loop.
