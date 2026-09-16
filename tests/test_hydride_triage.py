"""Tests for hydride candidate triage.

The load-bearing claim of this module is provenance: published values stay
published, judgment stays labelled as judgment, and nothing in between invents
a measurement. Most of these tests exist to hold that line.
"""

import glob
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import safety_gate
from orchestrator.workflow_parser import load_workflow
from policy.weighted_policy import WeightedPolicy
from triage.derive import (DerivationError, FeasibilityRules, parse_formula,
                           synthesis_feasibility, tc_confidence)
from triage.hydride_loader import FEASIBILITY_RULES, load, load_candidates
from triage.ranking import consensus_shortlist, rank, sensitivity
from triage.validation_plan import build_workflow, hypothesis_for, write_plan


@pytest.fixture(scope="module")
def candidates():
    return load()


@pytest.fixture(scope="module")
def policies():
    return [WeightedPolicy.from_yaml(p)
            for p in sorted(glob.glob("configs/policies/hydride_*.yaml"))]


@pytest.fixture(scope="module")
def rules():
    return FeasibilityRules.from_yaml(FEASIBILITY_RULES)


# --- the published dataset must stay a faithful transcription ---------------

def test_dataset_matches_the_published_tables(candidates):
    assert len(candidates) == 22, "paper publishes 18 perovskites + 4 fluorite-like"
    by_formula = {c.formula: c for c in candidates}

    # spot-check the headline candidate against Table 1 verbatim
    liz = by_formula["LiZrH6Ru"]
    assert (liz.lambda_ep, liz.omega_log_k, liz.tc_allen_dynes_k) == (1.00, 341.59, 23.5)
    assert liz.mat_id == "0f97a7734c"
    assert liz.tc_refined_k == 17.0

    # and the strongest-coupling one
    eucd = by_formula["EuCdH6Ru"]
    assert (eucd.lambda_ep, eucd.omega_log_k, eucd.tc_allen_dynes_k) == (2.53, 84.40, 13.6)


def test_only_one_candidate_has_a_refined_tc(candidates):
    """Most of this ranking rests on Allen-Dynes values the paper's own authors
    caution against over-reading. If that ever stops being true the triage
    narrative changes, so the count is asserted rather than assumed."""
    refined = [c for c in candidates if c.has_refined_tc]
    assert [c.formula for c in refined] == ["LiZrH6Ru"]


def test_missing_refined_tc_is_none_not_zero(candidates):
    """An empty cell means 'not reported'. Coercing it to 0.0 would invent the
    measurement 'this compound does not superconduct'."""
    unrefined = [c for c in candidates if not c.has_refined_tc]
    assert len(unrefined) == 21
    assert all(c.tc_refined_k is None for c in unrefined)
    assert all(c.tc_refined_method is None for c in unrefined)


def test_published_csv_carries_no_scores():
    """The provenance boundary is a file boundary: if a score ever appears in
    the published dataset, judgment has leaked into data."""
    with open("datasets/hydrides/gnome_hydride_candidates.csv") as f:
        header = f.readline().strip().lower()
    for forbidden in ("score", "weight", "rank", "priority", "feasibility", "confidence"):
        assert forbidden not in header, f"{forbidden!r} does not belong in published data"


# --- formula parsing --------------------------------------------------------

@pytest.mark.parametrize("formula,expected", [
    ("LiZrH6Ru", {"Li": 1, "Zr": 1, "H": 6, "Ru": 1}),
    ("Ta6MoH16", {"Ta": 6, "Mo": 1, "H": 16}),
    ("Ce2HRh6", {"Ce": 2, "H": 1, "Rh": 6}),
    ("EuLuTcH6", {"Eu": 1, "Lu": 1, "Tc": 1, "H": 6}),
])
def test_parse_formula(formula, expected):
    assert parse_formula(formula) == expected


def test_unknown_element_raises():
    with pytest.raises(DerivationError, match="not a known element"):
        parse_formula("XyH6")


def test_every_formula_in_the_dataset_parses(candidates):
    for c in candidates:
        assert parse_formula(c.formula)


# --- feasibility is judgment, and it is weakest-link ------------------------

def test_feasibility_takes_the_minimum_not_the_mean(rules):
    """One disqualifying constituent is not offset by convenient ones."""
    f = synthesis_feasibility("EuLuTcH6", rules)
    assert f["limiting_element"] == "Tc"
    assert f["score"] == 0.05
    # the mean over {Eu .65, Lu .65, Tc .05, H 1.0} would be ~0.59 — far too high
    assert f["score"] < 0.2


def test_technetium_candidates_are_flagged_infeasible(candidates):
    """Ten of the 22 contain technetium, which has no stable isotope. This is
    the single biggest practical constraint on the cohort."""
    tc_bearing = [c for c in candidates if "Tc" in parse_formula(c.formula)]
    assert len(tc_bearing) == 10
    assert all(c.metrics["synthesis_feasibility"] == 0.05 for c in tc_bearing)


def test_feasibility_records_why_not_just_a_number(rules):
    f = synthesis_feasibility("EuCdH6Ru", rules)
    assert f["limiting_element"] == "Cd"
    assert "toxic" in f["reason"]
    assert f["rule_set_id"] == "element_feasibility_v1"


# --- derived confidence -----------------------------------------------------

def test_strong_coupling_lowers_confidence():
    """The paper states Allen-Dynes fails for complex systems, and demonstrates
    it on its own top candidate."""
    assert tc_confidence(2.53, False)["score"] < tc_confidence(0.63, False)["score"]


def test_refinement_raises_confidence():
    assert tc_confidence(1.00, True)["score"] > tc_confidence(1.00, False)["score"]


# --- ranking and sensitivity ------------------------------------------------

def test_ranking_is_deterministic(candidates, policies):
    a = [rc.candidate.formula for rc in rank(candidates, policies[0])]
    b = [rc.candidate.formula for rc in rank(candidates, policies[0])]
    assert a == b


def test_policies_disagree_about_the_shortlist(candidates, policies):
    """If every policy produced the same ranking, the policy layer would be
    theatre and the sensitivity view would have nothing to report."""
    orders = {p.policy_id: [rc.candidate.formula for rc in rank(candidates, p)]
              for p in policies}
    assert len(set(map(tuple, orders.values()))) > 1


def test_feasibility_policy_promotes_the_makeable_candidates(candidates, policies):
    by_id = {p.policy_id: p for p in policies}
    feasible = [rc.candidate.formula
                for rc in rank(candidates, by_id["hydride_lab_feasible_first"])[:5]]
    high_tc = [rc.candidate.formula
               for rc in rank(candidates, by_id["hydride_high_tc_seeking"])[:5]]
    # the refractory Ta/Nb/Mo hydrides are the ones a lab could actually start on
    assert sum(f.startswith("Ta") for f in feasible) >= 3
    assert sum(f.startswith("Ta") for f in feasible) > sum(f.startswith("Ta") for f in high_tc)


def test_sensitivity_identifies_policy_driven_candidates(candidates, policies):
    sens = sensitivity(candidates, policies)
    assert any(r["stability"] == "policy-driven" for r in sens)
    assert any(r["stability"] == "stable" for r in sens)
    top = {r["formula"]: r for r in sens}
    assert top["LiZrH6Ru"]["rank_spread"] == 0, "the headline candidate leads under every policy"


def test_consensus_shortlist_is_policy_independent(candidates, policies):
    sens = sensitivity(candidates, policies)
    for r in consensus_shortlist(sens, top_n=5):
        assert all(v <= 5 for v in r["ranks"].values())


# --- THE ARCHITECTURAL CLAIM ------------------------------------------------

def test_generated_plan_runs_through_the_unchanged_orchestrator(candidates, policies, tmp_path):
    """Triage is an entry point into the existing loop, not a parallel module.

    A workflow the triage layer generated must parse with the same parser and be
    judged by the same safety gate as a CdTe experiment, with no special-casing.
    If this ever fails, the project is two demos in one repository again.
    """
    policy = policies[0]
    top = rank(candidates, policy)[0]
    path = write_plan(top, policy.policy_id, out_dir=str(tmp_path))

    wf = load_workflow(path)                      # the CdTe parser, unmodified
    assert wf.workflow_id.startswith("hydride_validation_")
    assert set(wf.param_bounds()) == {"anneal_temp_c", "anneal_time_h", "h2_pressure_bar"}

    # the CdTe safety gate, unmodified, on hazard rules it has never seen
    routine = {"anneal_temp_c": 600.0, "anneal_time_h": 24.0, "h2_pressure_bar": 80.0}
    assert safety_gate.review_parameters(wf, routine)["approval_status"] == "approved"

    # hot AND high-pressure: each bound legal, the combination is not
    unsafe = {"anneal_temp_c": 750.0, "anneal_time_h": 24.0, "h2_pressure_bar": 150.0}
    for name, (lo, hi) in wf.param_bounds().items():
        assert lo <= unsafe[name] <= hi, "precondition: every value in-bounds"
    verdict = safety_gate.review_parameters(wf, unsafe)
    assert verdict["approval_status"] == "blocked"
    assert verdict["blocked_by"] == "hydrogen_pressure_at_temperature"


def test_generated_plan_refuses_to_pretend_it_can_execute(candidates, policies):
    """No hydride devices exist and none will be fabricated."""
    top = rank(candidates, policies[0])[0]
    wf = build_workflow(top, policies[0].policy_id)
    assert wf["execution_status"]["state"] == "awaiting_device_implementation"


def test_plan_carries_provenance_back_to_the_published_row(candidates, policies):
    top = rank(candidates, policies[0])[0]
    prov = build_workflow(top, policies[0].policy_id)["provenance"]
    assert prov["candidate_id"] == top.candidate.candidate_id
    assert prov["mat_id"] == top.candidate.mat_id
    assert prov["selected_by_policy"] == policies[0].policy_id


def test_hypothesis_states_the_disagreement_it_would_settle(candidates, policies):
    top = rank(candidates, policies[0])[0]
    hyp = hypothesis_for(top, policies[0].policy_id)
    assert hyp["subject"] == "LiZrH6Ru"
    assert "23.5" in hyp["what_this_settles"] and "17" in hyp["what_this_settles"]
    assert hyp["negative_result_is_useful"] is True
    assert hyp["known_caveats"]
