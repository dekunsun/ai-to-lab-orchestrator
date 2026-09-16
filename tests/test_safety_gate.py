"""Tests for the safety gate — the part of the system that must not be decorative.

These exist because the gate's whole claim is that it can WITHHOLD lab time.
An untested gate that silently approves everything looks identical to a working
one in the demo output, which is exactly the failure mode worth guarding.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.workflow_parser import load_workflow
from orchestrator.executor import execute_workflow
from orchestrator import safety_gate
from devices.cdte.devices import build_cdte_devices
from devices.cdte import landscape

WORKFLOW = "configs/workflows/cdte_thin_film_solar_optimization.yaml"


@pytest.fixture(scope="module")
def wf():
    return load_workflow(WORKFLOW)


def _params(**overrides):
    base = {
        "cdte_thickness_nm": 2000.0,
        "substrate_temp_c": 460.0,
        "cdcl2_treatment_temp_c": 388.0,
        "cdcl2_treatment_time_min": 15.0,
        "dopant_pct": 0.6,
    }
    base.update(overrides)
    return base


def test_safe_parameters_are_approved(wf):
    review = safety_gate.review_parameters(wf, _params())
    assert review["approval_status"] == "approved"
    assert review["risk_level"] == "low"


def test_out_of_bounds_is_rejected(wf):
    """Reachable only from a human or LLM proposal — the optimizer samples
    in-bounds by construction, so this branch needs a test to stay honest."""
    review = safety_gate.review_parameters(wf, _params(cdcl2_treatment_temp_c=600.0))
    assert review["approval_status"] == "rejected"
    assert review["blocked_by"] == "out_of_bounds"


def test_missing_parameter_is_rejected(wf):
    p = _params()
    del p["dopant_pct"]
    assert safety_gate.review_parameters(wf, p)["approval_status"] == "rejected"


def test_individually_legal_but_jointly_unsafe_is_blocked(wf):
    """Each value is inside its own bounds; the combination is what is unsafe.
    This is the case bounds checking structurally cannot catch."""
    p = _params(cdcl2_treatment_temp_c=455.0, cdcl2_treatment_time_min=50.0)
    for name, (lo, hi) in wf.param_bounds().items():
        assert lo <= p[name] <= hi, "precondition: every value must be in-bounds"

    review = safety_gate.review_parameters(wf, p)
    assert review["approval_status"] == "blocked"
    assert review["blocked_by"] == "overtreatment_degradation_risk"


def test_flag_rule_warns_without_blocking(wf):
    review = safety_gate.review_parameters(wf, _params(cdcl2_treatment_temp_c=435.0))
    assert review["approval_status"] == "approved_with_flags"
    assert [f["name"] for f in review["hazard_flags"]] == ["approaching_overtreatment_cliff"]


def test_blocking_region_strictly_contains_the_failure_region(wf):
    """The regression that motivated this work: the hazard rule used to be a
    strict SUBSET of the surrogate's failure region, so every experiment it
    flagged was doomed anyway and the gate prevented nothing. The guardrail must
    be precautionary — it has to fire before the sample is actually destroyed."""
    rng = np.random.default_rng(0)
    names = list(landscape.BOUNDS)
    lo = np.array([landscape.BOUNDS[n][0] for n in names])
    hi = np.array([landscape.BOUNDS[n][1] for n in names])
    pts = lo + rng.random((20000, len(names))) * (hi - lo)

    unguarded_degradations = 0
    for row in pts:
        p = dict(zip(names, row))
        if landscape.failure_for(p) == "sample_degraded":
            if safety_gate.review_parameters(wf, p)["approval_status"] != "blocked":
                unguarded_degradations += 1
    assert unguarded_degradations == 0, (
        f"{unguarded_degradations} degrading parameter sets slipped past the gate")


def test_blocked_experiment_never_touches_a_device(wf):
    """A block must cost zero lab time — no device may run, no artifact appear."""
    devices = build_cdte_devices(np.random.default_rng(0))
    record = execute_workflow(
        wf, devices, _params(cdcl2_treatment_temp_c=460.0, cdcl2_treatment_time_min=55.0))

    assert record["status"] == "blocked"
    assert record["steps"] == [], "a blocked experiment must not execute any step"
    assert record["artifacts"] == []
    assert record["objective_score"] is None
    assert record["included_in_optimizer"] is False


def test_completed_experiment_is_eligible_for_optimizer_feedback(wf):
    devices = build_cdte_devices(np.random.default_rng(0))
    record = execute_workflow(wf, devices, _params())
    assert record["status"] == "completed"
    assert record["included_in_optimizer"] is True
    assert 0.0 <= record["objective_score"] <= 1.0
