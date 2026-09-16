"""Load published hydride candidates and derive the metrics a policy can score.

Keeps the provenance boundary that datasets/hydrides/SOURCE.md describes: the
CSV carries only what the paper printed, and everything a ranking needs on top
of that is computed here from documented rules.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from typing import Any

from triage.derive import (FeasibilityRules, best_available_tc, information_value,
                           synthesis_feasibility, tc_confidence)

DATASET = "datasets/hydrides/gnome_hydride_candidates.csv"
FEASIBILITY_RULES = "configs/triage/element_feasibility.yaml"

REQUIRED_COLUMNS = {"candidate_id", "mat_id", "formula", "structure_family",
                    "lambda_ep", "omega_log_k", "tc_allen_dynes_k"}


class DatasetError(ValueError):
    """Raised when the published dataset is malformed."""


def _opt_float(raw: str | None) -> float | None:
    """Empty means *not reported*, which is different from zero.

    Ten of the 22 columns this touches are genuinely empty because the paper
    never published a refined Tc for those compounds. Coercing that to 0.0 would
    invent a measurement of "this compound does not superconduct".
    """
    raw = (raw or "").strip()
    return float(raw) if raw else None


@dataclass
class HydrideCandidate:
    # --- published: transcribed from the paper ---
    candidate_id: str
    mat_id: str
    formula: str
    structure_family: str
    source_table: str
    lambda_ep: float
    omega_log_k: float
    tc_allen_dynes_k: float
    tc_refined_k: float | None
    tc_refined_method: str | None
    notes: str

    # --- derived: filled by derive_metrics(), never read from the CSV ---
    metrics: dict[str, float] = field(default_factory=dict)
    derivation: dict[str, Any] = field(default_factory=dict)

    @property
    def has_refined_tc(self) -> bool:
        return self.tc_refined_k is not None

    @property
    def best_tc_k(self) -> float:
        return self.tc_refined_k if self.has_refined_tc else self.tc_allen_dynes_k


def load_candidates(path: str = DATASET) -> list[HydrideCandidate]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise DatasetError(f"{path} is missing column(s): {sorted(missing)}")
        rows = list(reader)

    if not rows:
        raise DatasetError(f"{path} contains no candidates")

    out = []
    for i, r in enumerate(rows, start=2):  # start=2: row 1 is the header
        try:
            out.append(HydrideCandidate(
                candidate_id=r["candidate_id"], mat_id=r["mat_id"],
                formula=r["formula"], structure_family=r["structure_family"],
                source_table=r.get("source_table", ""),
                lambda_ep=float(r["lambda_ep"]),
                omega_log_k=float(r["omega_log_k"]),
                tc_allen_dynes_k=float(r["tc_allen_dynes_k"]),
                tc_refined_k=_opt_float(r.get("tc_refined_k")),
                tc_refined_method=(r.get("tc_refined_method") or "").strip() or None,
                notes=(r.get("notes") or "").strip(),
            ))
        except ValueError as e:
            raise DatasetError(f"{path} line {i}: {e}") from e

    ids = [c.candidate_id for c in out]
    if len(set(ids)) != len(ids):
        raise DatasetError(f"{path}: duplicate candidate_id values")
    return out


def derive_metrics(candidates: list[HydrideCandidate],
                   rules_path: str = FEASIBILITY_RULES) -> list[HydrideCandidate]:
    """Attach the four normalized metrics a policy scores.

    Tc is normalized against the best candidate *in this cohort*, not against an
    absolute scale. That makes the score a statement about relative priority
    within the set under review, which is what a triage decision actually is —
    and it means adding a better candidate correctly demotes everything else.
    """
    rules = FeasibilityRules.from_yaml(rules_path)
    max_tc = max(c.best_tc_k for c in candidates)
    if max_tc <= 0:
        raise DatasetError("no candidate has a positive Tc; nothing to rank")

    for c in candidates:
        tc = best_available_tc(c.tc_allen_dynes_k, c.tc_refined_k)
        conf = tc_confidence(c.lambda_ep, c.has_refined_tc)
        feas = synthesis_feasibility(c.formula, rules)

        tc_score = round(tc["value_k"] / max_tc, 4)
        c.metrics = {
            "tc_score": tc_score,
            "tc_confidence": conf["score"],
            "synthesis_feasibility": feas["score"],
            "information_value": information_value(tc_score, conf["score"]),
        }
        c.derivation = {
            "tc": tc, "confidence": conf, "feasibility": feas,
            "tc_normalized_against_k": max_tc,
            "provenance": {
                "tc_score": "derived from published Tc",
                "tc_confidence": "derived from published λ + refinement status",
                "synthesis_feasibility": f"analyst rule set {feas['rule_set_id']}",
                "information_value": "derived from tc_score and tc_confidence",
            },
        }
    return candidates


def load(path: str = DATASET, rules_path: str = FEASIBILITY_RULES) -> list[HydrideCandidate]:
    return derive_metrics(load_candidates(path), rules_path)
