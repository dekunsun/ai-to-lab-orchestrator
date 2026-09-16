"""Derived quantities for hydride triage — every rule written down.

The source paper publishes λ, ω_log and an Allen-Dynes Tc. It publishes no
score, no confidence and no feasibility. Ranking needs those, so this module
computes them from the published values, and the rules live here in the open
rather than inside a ranking function where nobody would find them.

Three tiers of provenance are kept distinct throughout the triage layer:

  published    the CSV in datasets/hydrides/ — transcribed from the paper
  derived      this module — a documented transform of published values
  analyst      configs/triage/element_feasibility.yaml — encoded judgment

Nothing here ever invents a measurement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

# Elements that appear in the transcribed tables, plus enough of the periodic
# table to catch a mis-parse. A formula token outside this set is an error, not
# something to silently skip.
KNOWN_ELEMENTS = {
    "H", "Li", "Be", "B", "C", "N", "O", "F", "Na", "Mg", "Al", "Si", "P", "S",
    "Cl", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru",
    "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Cs", "Ba", "La", "Ce",
    "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi",
}

_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")

# Allen-Dynes reliability bands. The paper is explicit that the
# McMillan-Allen-Dynes approach "has been developed using data from simple
# superconducting systems, and it is known to fail in describing systems with
# complex electronic properties". Strong coupling is where that bites, and the
# paper demonstrates it on its own top candidate: a careful multiband treatment
# of LiZrH6Ru landed at roughly half the Allen-Dynes number.
COUPLING_BANDS = [
    (1.5, 0.30, "λ ≥ 1.5 — strong coupling, where Allen-Dynes is least reliable"),
    (1.0, 0.55, "1.0 ≤ λ < 1.5 — moderate coupling, outside the best-validated range"),
    (0.0, 0.75, "λ < 1.0 — the regime Allen-Dynes was calibrated on"),
]
REFINEMENT_BONUS = 0.20


class DerivationError(ValueError):
    """Raised when a formula cannot be parsed or a rule table is malformed."""


# --------------------------------------------------------------------------
# formula parsing
# --------------------------------------------------------------------------
def parse_formula(formula: str) -> dict[str, int]:
    """Split a formula like 'LiZrH6Ru' into {'Li': 1, 'Zr': 1, 'H': 6, 'Ru': 1}."""
    counts: dict[str, int] = {}
    consumed = 0
    for symbol, count in _TOKEN.findall(formula):
        if symbol not in KNOWN_ELEMENTS:
            raise DerivationError(
                f"formula {formula!r}: {symbol!r} is not a known element symbol. "
                "Refusing to guess — a mis-parsed formula would silently corrupt "
                "every feasibility score derived from it.")
        counts[symbol] = counts.get(symbol, 0) + (int(count) if count else 1)
        consumed += len(symbol) + len(count)
    if consumed != len(formula):
        raise DerivationError(f"formula {formula!r} was only partly parsed")
    return counts


# --------------------------------------------------------------------------
# analyst rule table
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class FeasibilityRules:
    rule_set_id: str
    elements: dict[str, dict[str, Any]]
    default: dict[str, Any]

    @classmethod
    def from_yaml(cls, path: str) -> "FeasibilityRules":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        if data.get("combine") != "min":
            raise DerivationError(
                "only combine: min is supported. Feasibility is a weakest-link "
                "property — averaging would let convenient elements offset a "
                "disqualifying one.")
        return cls(rule_set_id=data["rule_set_id"], elements=data["elements"],
                   default=data["defaults"])

    def for_element(self, symbol: str) -> dict[str, Any]:
        return self.elements.get(symbol, self.default)


def synthesis_feasibility(formula: str, rules: FeasibilityRules) -> dict[str, Any]:
    """Weakest-link feasibility over a formula's elements, with the reason kept.

    The binding element is returned alongside the score, because "0.05" is not
    actionable and "contains technetium, which has no stable isotope" is.
    """
    elements = parse_formula(formula)
    scored = [(sym, self_rule["score"], self_rule["reason"])
              for sym in elements
              for self_rule in [rules.for_element(sym)]]
    symbol, score, reason = min(scored, key=lambda t: t[1])
    return {"score": float(score), "limiting_element": symbol, "reason": reason,
            "rule_set_id": rules.rule_set_id}


# --------------------------------------------------------------------------
# derived confidence and Tc selection
# --------------------------------------------------------------------------
def tc_confidence(lambda_ep: float, has_refined: bool, has_measured: bool = False,
                  calibration_penalty: float = 0.0) -> dict[str, Any]:
    """How much to trust this candidate's Tc, given how it was obtained.

    A measured value outranks any calculation, so direct evidence short-circuits
    the coupling-regime reasoning entirely. Absent that, a method-level
    calibration penalty applies: if the method has been caught running high on
    the compounds we did measure, every un-measured prediction it produced is
    worth less than it was yesterday.
    """
    if has_measured:
        from triage.evidence import MEASURED_CONFIDENCE
        return {"score": MEASURED_CONFIDENCE,
                "rationale": "measured directly; only sample-quality and instrument "
                             "uncertainty remain"}

    for threshold, base, rationale in COUPLING_BANDS:
        if lambda_ep >= threshold:
            break
    score = base + (REFINEMENT_BONUS if has_refined else 0.0)
    score = min(1.0, score) * (1.0 - calibration_penalty)
    rationale += ("; a beyond-Allen-Dynes calculation exists" if has_refined
                  else "; Allen-Dynes only, not independently refined")
    if calibration_penalty > 0:
        rationale += (f"; reduced {calibration_penalty:.0%} by evidence that the "
                      f"method runs high")
    return {"score": round(score, 4), "rationale": rationale}


def best_available_tc(tc_allen_dynes: float, tc_refined: float | None,
                      tc_measured: float | None = None) -> dict[str, Any]:
    """Prefer a refined Tc where one exists, and say which was used.

    Only one of the 22 candidates has been refined, so most of this ranking
    rests on a number the paper's own authors caution against over-reading.
    Recording `method` keeps that visible instead of flattening both kinds of
    estimate into one indistinguishable column.
    """
    if tc_measured is not None:
        # A measurement supersedes every calculation. The predicted values are
        # kept alongside it so the size of the miss stays on the record.
        return {"value_k": tc_measured, "method": "measured",
                "allen_dynes_k": tc_allen_dynes, "refined_k": tc_refined,
                "delta_vs_allen_dynes": round(tc_measured - tc_allen_dynes, 2)}
    if tc_refined is not None:
        return {"value_k": tc_refined, "method": "refined",
                "allen_dynes_k": tc_allen_dynes,
                "delta_vs_allen_dynes": round(tc_refined - tc_allen_dynes, 2)}
    return {"value_k": tc_allen_dynes, "method": "allen_dynes",
            "allen_dynes_k": tc_allen_dynes, "delta_vs_allen_dynes": None}


def information_value(tc_score: float, confidence: float) -> float:
    """Value of measuring this candidate, as opposed to value of having it.

    Highest where a high predicted Tc rests on a weak estimate: that is exactly
    the disagreement an experiment would resolve. It is what makes a negative
    result worth collecting, and it is why a triage policy should be able to
    weight learning separately from payoff.
    """
    return round(tc_score * (1.0 - confidence), 4)
