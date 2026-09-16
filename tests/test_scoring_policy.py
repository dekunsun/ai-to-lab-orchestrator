"""Tests for weighted decision policies.

The point of this layer is that the most contestable assumption in the system —
how competing objectives trade off — is explicit, validated, versioned, and
recorded. These tests hold that line.
"""

import glob
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy.weighted_policy import WeightedPolicy, PolicyError
from devices.cdte.devices import build_cdte_devices, DEFAULT_CDTE_POLICY
from orchestrator.workflow_parser import load_workflow
from orchestrator.executor import execute_workflow

WORKFLOW = "configs/workflows/cdte_thin_film_solar_optimization.yaml"

GOOD_PARAMS = {
    "cdte_thickness_nm": 2000.0,
    "substrate_temp_c": 460.0,
    "cdcl2_treatment_temp_c": 388.0,
    "cdcl2_treatment_time_min": 15.0,
    "dopant_pct": 0.6,
}


# --- policy file validation ------------------------------------------------

@pytest.mark.parametrize("path", sorted(glob.glob("configs/policies/*.yaml")))
def test_shipped_policies_are_valid(path):
    """Every policy in the repo must load and satisfy the invariants."""
    p = WeightedPolicy.from_yaml(path)
    assert p.policy_id
    assert abs(sum(p.weights.values()) - 1.0) < 1e-6


def test_weights_must_sum_to_one():
    """Otherwise a policy could score higher just by weighing more, and scores
    would stop being comparable across policies."""
    with pytest.raises(PolicyError, match="sum to 1.0"):
        WeightedPolicy.from_dict({"policy_id": "bad", "weights": {"a": 0.5, "b": 0.9}})


def test_negative_weights_rejected():
    with pytest.raises(PolicyError, match="non-negative"):
        WeightedPolicy.from_dict({"policy_id": "bad", "weights": {"a": 1.5, "b": -0.5}})


def test_missing_metric_raises_instead_of_scoring_zero():
    """A typo in a policy must fail loudly. Silently substituting 0.0 would let
    it quietly change every decision the system makes."""
    p = WeightedPolicy.from_dict({"policy_id": "p", "weights": {"a": 0.5, "typo": 0.5}})
    with pytest.raises(PolicyError, match="typo"):
        p.score({"a": 1.0})


def test_contributions_sum_to_score_and_explain_it():
    p = WeightedPolicy.from_dict({"policy_id": "p", "weights": {"a": 0.75, "b": 0.25}})
    metrics = {"a": 0.8, "b": 0.4}
    contrib = p.contributions(metrics)
    assert contrib == pytest.approx({"a": 0.6, "b": 0.1})
    assert p.score(metrics) == pytest.approx(sum(contrib.values()))


def test_contributions_are_not_pre_rounded():
    """Rounding a term before it feeds a decision perturbed the objective by 1e-4,
    which was enough to redirect the entire Bayesian search. Regression guard."""
    p = WeightedPolicy.from_dict({"policy_id": "p", "weights": {"a": 1.0}})
    assert p.score({"a": 0.1234567891}) == pytest.approx(0.1234567891, abs=1e-12)


# --- policy actually drives the decision -----------------------------------

def test_policies_rank_the_same_measurements_differently():
    """The whole argument: identical experimental data, different priorities,
    different answer. If this ever passed trivially the layer would be theatre."""
    perf = WeightedPolicy.from_yaml("configs/policies/cdte_performance_first.yaml")
    manu = WeightedPolicy.from_yaml("configs/policies/cdte_manufacturability_first.yaml")

    hero_cell = {"pce_proxy": 0.90, "crystallinity_score": 0.50,
                 "phase_purity": 0.50, "defect_passivation_score": 0.50}
    clean_process = {"pce_proxy": 0.60, "crystallinity_score": 0.90,
                     "phase_purity": 0.90, "defect_passivation_score": 0.85}

    assert perf.score(hero_cell) > perf.score(clean_process)
    assert manu.score(clean_process) > manu.score(hero_cell)


def test_default_policy_matches_the_benchmarked_weights():
    """Guards the README: its numbers were produced under exactly these weights."""
    p = WeightedPolicy.from_yaml(DEFAULT_CDTE_POLICY)
    assert p.weights == {"pce_proxy": 0.45, "crystallinity_score": 0.20,
                         "defect_passivation_score": 0.20, "phase_purity": 0.15}


# --- provenance -------------------------------------------------------------

def test_experiment_records_which_policy_scored_it():
    """Provenance is not only how data was measured — it is also which
    trade-off turned that data into a decision."""
    wf = load_workflow(WORKFLOW)
    pol = WeightedPolicy.from_yaml("configs/policies/cdte_performance_first.yaml")
    devices = build_cdte_devices(np.random.default_rng(0), pol)
    record = execute_workflow(wf, devices, GOOD_PARAMS)

    assert record["status"] == "completed"
    assert record["policy_id"] == "cdte_performance_first"

    scoring_step = [s for s in record["steps"] if s["device"] == "scoring_engine"][0]
    assert scoring_step["metadata"]["weights"] == pol.weights
    assert scoring_step["metadata"]["contributions"].keys() == pol.weights.keys()


def test_same_experiment_scores_differently_under_different_policies():
    """Same parameters, same noise seed, same measurements — only the policy
    differs, so any score difference is attributable to the policy alone."""
    wf = load_workflow(WORKFLOW)
    scores = {}
    for name in ("cdte_performance_first", "cdte_manufacturability_first"):
        devices = build_cdte_devices(
            np.random.default_rng(7), f"configs/policies/{name}.yaml")
        scores[name] = execute_workflow(wf, devices, GOOD_PARAMS)["objective_score"]
    assert scores["cdte_performance_first"] != scores["cdte_manufacturability_first"]
