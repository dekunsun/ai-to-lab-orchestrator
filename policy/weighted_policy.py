"""Weighted decision policies — shared by CdTe scoring and hydride triage.

WHY THIS EXISTS
---------------
Both halves of this system end up collapsing several measured or published
quantities into ONE number that drives a decision:

  * CdTe:     pce_proxy, crystallinity, phase purity, passivation -> objective
  * Hydrides: refined Tc, stability, feasibility, confidence      -> priority

Those weights are not physical constants. They encode what a team currently
cares about — raw performance, or a process that reproduces, or candidates that
will give clean validation data. Burying them as literals inside a device or a
ranking function hides the single most contestable assumption in the system.

So they live in `configs/policies/*.yaml`, they are versioned, they are recorded
against every experiment they scored, and they can be swapped without touching
any execution code. "Which policy produced this number?" is always answerable.

DESIGN NOTES
------------
* Weights must be non-negative and sum to 1.0. That is not mathematically
  required, but it keeps scores comparable across policies — otherwise a policy
  could look better simply by weighing more.
* A metric named in a policy but absent from the data raises. A silent 0.0 would
  let a typo quietly change every decision the system makes, which is the exact
  failure mode this module exists to prevent.
* `contributions()` exposes the per-term breakdown, so a dashboard can show WHY
  something scored as it did rather than only the total.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

WEIGHT_SUM_TOLERANCE = 1e-6


class PolicyError(ValueError):
    """Raised for a malformed policy file or a policy/data mismatch."""


@dataclass(frozen=True)
class WeightedPolicy:
    policy_id: str
    name: str
    weights: dict[str, float]
    description: str = ""
    applies_to: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # -- construction ------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str = "<dict>") -> "WeightedPolicy":
        for key in ("policy_id", "weights"):
            if key not in data:
                raise PolicyError(f"policy {source} is missing required key '{key}'")

        weights = data["weights"]
        if not isinstance(weights, dict) or not weights:
            raise PolicyError(f"policy {source}: 'weights' must be a non-empty mapping")

        bad = {k: v for k, v in weights.items() if not isinstance(v, (int, float)) or v < 0}
        if bad:
            raise PolicyError(f"policy {source}: weights must be non-negative numbers, got {bad}")

        total = sum(weights.values())
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise PolicyError(
                f"policy {source}: weights must sum to 1.0 (got {total:.6f}). "
                "Normalized weights keep scores comparable between policies.")

        return cls(
            policy_id=data["policy_id"],
            name=data.get("name", data["policy_id"]),
            weights={k: float(v) for k, v in weights.items()},
            description=data.get("description", ""),
            applies_to=data.get("applies_to", ""),
            raw=data,
        )

    @classmethod
    def from_yaml(cls, path: str) -> "WeightedPolicy":
        with open(path, "r") as f:
            return cls.from_dict(yaml.safe_load(f), source=path)

    # -- scoring -----------------------------------------------------------
    def _require(self, metrics: dict[str, Any]) -> None:
        missing = [m for m in self.weights if m not in metrics]
        if missing:
            raise PolicyError(
                f"policy '{self.policy_id}' needs metric(s) {missing}, which the "
                f"available data does not provide (have: {sorted(metrics)}). "
                "Refusing to score rather than silently treating them as zero.")

    def contributions(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Per-term contribution to the final score — the 'why' behind the number.

        Deliberately NOT rounded. An earlier version rounded each term to 6
        decimal places, which perturbed the objective by up to 1e-4. That is
        numerically meaningless but not behaviourally meaningless: it changed
        which point the GP considered incumbent, which changed the argmax of
        Expected Improvement, which sent the whole search down a different path.
        Round for display, never before a decision.
        """
        self._require(metrics)
        return {m: w * float(metrics[m]) for m, w in self.weights.items()}

    def score(self, metrics: dict[str, Any]) -> float:
        """Weighted sum, clipped to [0, 1]. Inputs are expected to be normalized."""
        total = sum(self.contributions(metrics).values())
        return float(min(1.0, max(0.0, total)))

    def provenance(self) -> dict[str, Any]:
        """What gets recorded alongside any score this policy produced."""
        return {"policy_id": self.policy_id, "policy_name": self.name,
                "weights": dict(self.weights)}
