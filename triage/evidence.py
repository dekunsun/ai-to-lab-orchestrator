"""Evidence: what a measurement does to a hypothesis, and to everything near it.

The system does not manufacture evidence. There are no hydride devices here and
none will be fabricated, so evidence enters from outside — an instrument run, a
collaborator's report, a published measurement. What this module owns is what
happens next: validating the record, deciding what it settles, and propagating
the consequences back into the ranking that proposed the experiment.

Two ideas carry most of the weight.

**A null result is meaningless without its floor.** "We saw no transition" says
nothing until you know the lowest temperature probed. If a rig only reached 20 K
and the prediction was 17 K, the experiment could not have observed the thing it
was testing, and calling that a refutation would be wrong. That case is
`inconclusive`, and it is the single most important branch here.

**Evidence about one compound is evidence about the method.** If Allen-Dynes
overestimates on the compound we measured, that bears on the other twenty-one
candidates that rest on Allen-Dynes alone. So evidence updates a method-level
calibration as well as the candidate it came from.

What this module deliberately does NOT do is rewrite a prediction. A calibration
factor lowers *confidence* in the method's numbers; it never silently produces a
"corrected" Tc. Adjusting the estimate would manufacture a value nobody computed.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from typing import Any

# How far a measurement may sit from a prediction and still count as supporting
# it. This is a decision-policy parameter, not a law — 25% is loose enough to
# survive ordinary measurement and sample-quality scatter, tight enough that the
# 23.5 K -> 17 K disagreement the paper itself flags would register.
DEFAULT_TOLERANCE = 0.25

# A measured value still carries sample-quality and instrument uncertainty, so
# direct evidence raises confidence but never to 1.0.
MEASURED_CONFIDENCE = 0.95

# Cap on how much a method-level calibration may erode confidence. Evidence from
# a handful of compounds should move the needle, not dominate it.
MAX_CALIBRATION_PENALTY = 0.30

SOURCE_TYPES = {"measured", "published", "collaborator_report", "hypothetical_example"}


class EvidenceError(ValueError):
    """Raised for a malformed or unattributable evidence record."""


@dataclass
class Evidence:
    evidence_id: str
    candidate_id: str
    formula: str
    observed_tc_k: float | None       # None = no transition seen
    measurement_floor_k: float        # lowest temperature actually probed
    method: str                       # four_point_resistivity / squid_susceptibility / ...
    source_type: str
    source: str
    recorded_by: str
    notes: str = ""

    @property
    def is_hypothetical(self) -> bool:
        return self.source_type == "hypothetical_example"

    @property
    def is_null_result(self) -> bool:
        return self.observed_tc_k is None


def _opt_float(raw: str | None) -> float | None:
    raw = (raw or "").strip()
    return float(raw) if raw else None


def load_evidence(path: str) -> list[Evidence]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for i, r in enumerate(rows, start=2):
        st = (r.get("source_type") or "").strip()
        if st not in SOURCE_TYPES:
            raise EvidenceError(
                f"{path} line {i}: source_type {st!r} must be one of {sorted(SOURCE_TYPES)}. "
                "Evidence without a stated provenance is not evidence.")
        if not (r.get("recorded_by") or "").strip():
            raise EvidenceError(
                f"{path} line {i}: recorded_by is required — a measurement nobody is "
                "willing to sign for cannot be used to overturn a prediction.")
        floor = _opt_float(r.get("measurement_floor_k"))
        if floor is None:
            raise EvidenceError(
                f"{path} line {i}: measurement_floor_k is required. A null result is "
                "uninterpretable without the lowest temperature actually probed.")
        out.append(Evidence(
            evidence_id=r["evidence_id"], candidate_id=r["candidate_id"],
            formula=r["formula"], observed_tc_k=_opt_float(r.get("observed_tc_k")),
            measurement_floor_k=floor, method=(r.get("method") or "").strip(),
            source_type=st, source=(r.get("source") or "").strip(),
            recorded_by=r["recorded_by"].strip(), notes=(r.get("notes") or "").strip()))
    return out


# --------------------------------------------------------------------------
# what a record settles
# --------------------------------------------------------------------------
def assess(ev: Evidence, predicted_tc_k: float,
           tolerance: float = DEFAULT_TOLERANCE) -> dict[str, Any]:
    """Decide what one evidence record does to one prediction."""
    if ev.is_null_result:
        if ev.measurement_floor_k >= predicted_tc_k:
            return {
                "status": "inconclusive",
                "direction": None,
                "reason": (
                    f"No transition seen, but the rig only reached "
                    f"{ev.measurement_floor_k:g} K and the prediction is "
                    f"{predicted_tc_k:g} K. This experiment could not have observed "
                    f"the transition it was testing — it refutes nothing."),
                "ratio": None,
            }
        return {
            "status": "contradicted",
            "direction": "overestimate",
            "reason": (
                f"No transition down to {ev.measurement_floor_k:g} K, well below the "
                f"predicted {predicted_tc_k:g} K. The prediction had room to be seen "
                f"and was not."),
            # a null below the floor bounds Tc from above; treat the floor as the
            # optimistic upper bound when calibrating, rather than claiming zero
            "ratio": ev.measurement_floor_k / predicted_tc_k,
        }

    ratio = ev.observed_tc_k / predicted_tc_k
    rel = abs(ev.observed_tc_k - predicted_tc_k) / predicted_tc_k
    if rel <= tolerance:
        return {"status": "supported", "direction": None, "ratio": ratio,
                "reason": (f"Measured {ev.observed_tc_k:g} K against a predicted "
                           f"{predicted_tc_k:g} K — within the {tolerance:.0%} tolerance.")}
    over = ev.observed_tc_k < predicted_tc_k
    return {
        "status": "contradicted",
        "direction": "overestimate" if over else "underestimate",
        "ratio": ratio,
        "reason": (f"Measured {ev.observed_tc_k:g} K against a predicted "
                   f"{predicted_tc_k:g} K — a {rel:.0%} "
                   f"{'over' if over else 'under'}estimate, outside the "
                   f"{tolerance:.0%} tolerance."),
    }


# --------------------------------------------------------------------------
# what it implies about the method
# --------------------------------------------------------------------------
@dataclass
class Calibration:
    method: str
    n: int
    factor: float | None            # median observed/predicted; <1 means it runs high
    penalty: float                  # confidence multiplier reduction, capped
    inconclusive: int = 0
    detail: list[dict[str, Any]] = field(default_factory=list)

    def describe(self) -> str:
        if self.factor is None:
            return (f"No usable evidence on {self.method} yet"
                    + (f" ({self.inconclusive} inconclusive)" if self.inconclusive else "")
                    + ".")
        pct = abs(1.0 - self.factor) * 100
        way = "high" if self.factor < 1 else "low"
        return (f"On {self.n} conclusive measurement(s), {self.method} runs "
                f"{pct:.0f}% {way} (median observed/predicted = {self.factor:.2f}). "
                f"Confidence in every un-measured {self.method} prediction is reduced "
                f"by {self.penalty:.0%}.")


def calibrate(assessments: list[dict[str, Any]], method: str = "allen_dynes") -> Calibration:
    """Turn conclusive evidence into a method-level confidence adjustment.

    Inconclusive records are excluded rather than counted as agreement — an
    experiment that could not have seen the effect is not evidence the effect
    is absent, and letting it vote would quietly reward under-powered runs.
    """
    usable = [a for a in assessments
              if a["status"] != "inconclusive" and a.get("ratio") is not None]
    inconclusive = sum(1 for a in assessments if a["status"] == "inconclusive")
    if not usable:
        return Calibration(method=method, n=0, factor=None, penalty=0.0,
                           inconclusive=inconclusive)

    factor = statistics.median(a["ratio"] for a in usable)
    penalty = min(MAX_CALIBRATION_PENALTY, abs(1.0 - factor) * 0.5)
    return Calibration(method=method, n=len(usable), factor=round(factor, 4),
                       penalty=round(penalty, 4), inconclusive=inconclusive,
                       detail=usable)
