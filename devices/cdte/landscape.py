"""CdTe literature-inspired surrogate landscape.

WHAT THIS IS
------------
A transparent, deterministic "ground-truth" response surface over the CdTe
process parameters, plus rules for observation noise and experiment failure.
It is the environment our orchestrator + optimizer run against.

WHAT THIS IS NOT
----------------
A physical model of CdTe solar cells. None of these numbers predict real PCE.
The point is to give the optimizer a landscape with the *qualitative* messiness
of a real process — a non-smooth treatment window, an over-treatment cliff,
interacting parameters, noise, and outright failures — so that "Bayesian
optimization beats random" is a claim about sample efficiency under realistic
difficulty, not an artifact of a smooth toy bowl.

The qualitative behaviors encoded here (all literature-inspired, not fitted):
  - CdCl2 activation has a *window*: too cold under-activates, a good band in
    the middle, and a sharp drop ("cliff") when too hot.  ~360 / 360-415 / >430 C
  - Absorber thickness has an optimum band; too thin loses absorption, too thick
    hurts collection.
  - Substrate temperature too low -> poor crystallinity (can fail outright).
  - Treatment time interacts with treatment temperature: hot AND long -> degrade.
  - Light doping helps; too much hurts.

All bounds match configs/workflows/cdte_*.yaml.
"""

from __future__ import annotations
import math
from dataclasses import dataclass


# ----- parameter reference bounds (kept in sync with the workflow YAML) -----
BOUNDS = {
    "cdte_thickness_nm": (800.0, 4000.0),
    "substrate_temp_c": (250.0, 550.0),
    "cdcl2_treatment_temp_c": (330.0, 470.0),
    "cdcl2_treatment_time_min": (5.0, 60.0),
    "dopant_pct": (0.0, 3.0),
}


def _bell(x: float, center: float, width: float) -> float:
    """Gaussian bump in [0,1], =1 at center."""
    return math.exp(-((x - center) ** 2) / (2.0 * width ** 2))


@dataclass
class LandscapeComponents:
    """The named pieces that go into the score — exposed so the dashboard /
    interview can show *why* a point scored as it did, not just the number."""
    thickness_term: float
    substrate_term: float
    treatment_window_term: float
    overtreatment_penalty: float
    doping_term: float
    interaction_penalty: float


def true_components(params: dict[str, float]) -> LandscapeComponents:
    t_nm = params["cdte_thickness_nm"]
    sub_c = params["substrate_temp_c"]
    treat_c = params["cdcl2_treatment_temp_c"]
    treat_min = params["cdcl2_treatment_time_min"]
    dop = params["dopant_pct"]

    # Absorber thickness: optimum band around ~2000 nm (fairly tight).
    thickness_term = _bell(t_nm, center=2000.0, width=480.0)

    # Substrate temperature: rises then saturates; very low is bad.
    substrate_term = _bell(sub_c, center=460.0, width=80.0)

    # CdCl2 treatment *window* — the signature non-smooth feature.
    # Good band centered ~388 C; narrow, with a hard cliff when hot.
    window = _bell(treat_c, center=388.0, width=14.0)
    # Over-treatment cliff: sigmoidal penalty that switches on past ~425 C.
    overtreat = 1.0 / (1.0 + math.exp(-(treat_c - 428.0) / 3.0))  # 0..1
    treatment_window_term = window
    overtreatment_penalty = overtreat

    # Doping: light is good (~0.6%), too much degrades (tight).
    doping_term = _bell(dop, center=0.6, width=0.45)

    # Interaction: hot AND long treatment compounds degradation.
    # normalized 0..1 each, multiplied.
    hot = max(0.0, (treat_c - 400.0) / (470.0 - 400.0))
    long = max(0.0, (treat_min - 30.0) / (60.0 - 30.0))
    interaction_penalty = hot * long

    return LandscapeComponents(
        thickness_term=thickness_term,
        substrate_term=substrate_term,
        treatment_window_term=treatment_window_term,
        overtreatment_penalty=overtreatment_penalty,
        doping_term=doping_term,
        interaction_penalty=interaction_penalty,
    )


def true_score(params: dict[str, float]) -> float:
    """Noise-free 'true' objective in [0,1]. The optimizer never sees this
    directly — it only sees noisy observations via the devices."""
    c = true_components(params)
    base = (
        0.34 * c.treatment_window_term
        + 0.24 * c.thickness_term
        + 0.20 * c.substrate_term
        + 0.12 * c.doping_term
    )
    # apply multiplicative-ish penalties (cliff + interaction)
    score = base * (1.0 - 0.85 * c.overtreatment_penalty) * (1.0 - 0.6 * c.interaction_penalty)
    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Failure rules: some parameter regions don't yield a usable measurement at all.
# Returning failure (not a low score) is deliberate — negative results are
# first-class data in a real self-driving lab.
# ---------------------------------------------------------------------------
def failure_for(params: dict[str, float]) -> str | None:
    treat_c = params["cdcl2_treatment_temp_c"]
    treat_min = params["cdcl2_treatment_time_min"]
    sub_c = params["substrate_temp_c"]

    # Hot + long -> sample degrades, no valid device.
    if treat_c > 450.0 and treat_min > 45.0:
        return "sample_degraded"
    # Too-cold substrate -> film never crystallizes enough to measure.
    if sub_c < 285.0:
        return "low_crystallinity"
    return None
