# Data Sources & Research-to-Product Notes

This project is part of a broader exercise in translating recent materials science research into product-oriented project ideas. For each paper or research direction, I focus on three questions:

1. What did the research make possible?
2. What remains difficult to operationalize?
3. What kind of product, workflow, or system could help bridge that gap?

The goal is not only to cite the underlying research, but to show how a product-oriented builder might turn a frontier research result into a concrete tool, workflow, or validation system.

## Hydride Superconductor Data

### Source

Sanna et al., “Search for thermodynamically stable ambient pressure superconducting hydrides in the GNoME database,” *Communications Physics*, 2026.
https://www.nature.com/articles/s42005-026-02552-4

### What the Paper Provides

This paper provides the lambda, omega_log, and Allen–Dynes Tc values for the 25 candidate hydrides used in the triage use case, as reported in Tables 1 and 2. The values in `configs/data/hydrides.csv` are taken directly from the paper and are used as published reference data.

### Product Translation

The paper screens a large computational database for promising ambient pressure superconductors and identifies candidates such as LiZrH6Ru, which has the highest reported Tc among the candidates.

From a product perspective, the key insight is that a ranked list of predicted materials is only the beginning of the discovery workflow. A lab still needs to decide which candidates are worth validating first, based on factors such as synthesizability, stability, cost, experimental risk, and policy constraints.

This creates a project opportunity: turn computational screening outputs into a prioritized validation plan that can support lab decision making. The hydride triage use case is designed around this opportunity.

## CdTe Surrogate Environment

### Source

This environment is literature inspired rather than based on a single dataset. It uses an abstract response surface whose qualitative behavior reflects well known CdTe thin film process patterns, including an optimal CdCl2 treatment window, performance degradation from over processing, and sensitivity to substrate temperature.

### Reference Point

First Solar Series 7 represents a state of the art commercial CdTe module line. Its public datasheets show that CdTe is a mature technology with tightly controlled manufacturing processes. The surrogate environment is designed as a benchmark environment rather than a direct predictor of commercial PCE.

### Product Translation

CdTe manufacturing shows why materials optimization is not only a prediction problem. Real process landscapes are noisy, costly to sample, and often include failure regions. A useful system needs to explore efficiently, learn from limited experiments, and avoid wasting lab capacity on low value trials.

This creates a project opportunity: build a closed loop optimization benchmark that tests whether an AI system can propose better experiments over time under realistic process difficulty.

## Background Context

GNoME, released by Google DeepMind in 2023, predicted around 2.2 million stable crystals, greatly expanding the known materials search space. Its key limitation is that prediction alone does not complete the experimental validation process.

This prediction to validation gap is the strategic backdrop for lab in the loop and self driving lab systems. It is also the conceptual origin of this orchestrator project.

### One Line Framing

GNoME expanded the search space to around 2.2 million predicted stable crystals. The next bottleneck is experimental validation. An AI to lab orchestrator is one way to help close that loop.
