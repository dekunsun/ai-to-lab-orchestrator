"""Tests for the evidence loop.

The loop's job is to let a measurement change a decision. These tests hold the
two judgments that make it worth having: that an under-powered experiment is not
a refutation, and that evidence about one compound is evidence about the method.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy.weighted_policy import WeightedPolicy
from triage.evidence import (Evidence, EvidenceError, MAX_CALIBRATION_PENALTY,
                             assess, calibrate, load_evidence)
from triage.hydride_loader import derive_metrics, load, load_candidates
from triage.ranking import rank

EXAMPLE = "datasets/hydrides/evidence_example.csv"
POLICY = "configs/policies/hydride_balanced_validation.yaml"


def ev(**kw):
    base = dict(evidence_id="EV-T", candidate_id="HYD-018", formula="LiZrH6Ru",
                observed_tc_k=None, measurement_floor_k=1.8, method="four_point",
                source_type="measured", source="rig-1", recorded_by="tester", notes="")
    base.update(kw)
    return Evidence(**base)


# --- the judgment that matters most ----------------------------------------

def test_null_result_above_the_floor_is_inconclusive_not_refutation():
    """A rig that only reached 20 K cannot refute a 17 K prediction. Calling
    that a contradiction would be the most damaging mistake this module could
    make, because it would discard a real candidate on no evidence."""
    a = assess(ev(observed_tc_k=None, measurement_floor_k=20.0), predicted_tc_k=17.0)
    assert a["status"] == "inconclusive"
    assert "could not have observed" in a["reason"]


def test_null_result_below_the_floor_is_a_refutation():
    a = assess(ev(observed_tc_k=None, measurement_floor_k=1.8), predicted_tc_k=17.0)
    assert a["status"] == "contradicted"
    assert a["direction"] == "overestimate"


def test_measurement_within_tolerance_supports():
    a = assess(ev(observed_tc_k=6.2, measurement_floor_k=1.8), predicted_tc_k=7.0)
    assert a["status"] == "supported"


def test_measurement_far_below_contradicts_and_names_the_direction():
    a = assess(ev(observed_tc_k=9.4, measurement_floor_k=1.8), predicted_tc_k=17.0)
    assert a["status"] == "contradicted"
    assert a["direction"] == "overestimate"
    assert a["ratio"] == pytest.approx(9.4 / 17.0)


def test_measurement_far_above_also_contradicts():
    """A prediction missed in the happy direction is still a missed prediction."""
    a = assess(ev(observed_tc_k=30.0, measurement_floor_k=1.8), predicted_tc_k=17.0)
    assert a["status"] == "contradicted"
    assert a["direction"] == "underestimate"


# --- provenance is mandatory ------------------------------------------------

def test_evidence_requires_a_measurement_floor(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("evidence_id,candidate_id,formula,observed_tc_k,measurement_floor_k,"
                 "method,source_type,source,recorded_by,notes\n"
                 "EV-1,HYD-018,LiZrH6Ru,,,squid,measured,rig,tester,\n")
    with pytest.raises(EvidenceError, match="measurement_floor_k"):
        load_evidence(str(p))


def test_evidence_requires_an_attributable_recorder(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("evidence_id,candidate_id,formula,observed_tc_k,measurement_floor_k,"
                 "method,source_type,source,recorded_by,notes\n"
                 "EV-1,HYD-018,LiZrH6Ru,9.4,1.8,squid,measured,rig,,\n")
    with pytest.raises(EvidenceError, match="recorded_by"):
        load_evidence(str(p))


def test_unknown_source_type_rejected(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("evidence_id,candidate_id,formula,observed_tc_k,measurement_floor_k,"
                 "method,source_type,source,recorded_by,notes\n"
                 "EV-1,HYD-018,LiZrH6Ru,9.4,1.8,squid,vibes,rig,tester,\n")
    with pytest.raises(EvidenceError, match="source_type"):
        load_evidence(str(p))


def test_shipped_example_is_marked_hypothetical():
    """Nobody has measured these compounds. If this file ever stops announcing
    that, the project is presenting invented measurements as results."""
    records = load_evidence(EXAMPLE)
    assert records
    assert all(r.is_hypothetical for r in records)


# --- method-level calibration ----------------------------------------------

def test_inconclusive_records_do_not_vote_in_the_calibration():
    """Otherwise an under-powered run would count as agreement, which quietly
    rewards experiments that could not have failed."""
    conclusive = assess(ev(observed_tc_k=9.4), predicted_tc_k=17.0)
    weak = assess(ev(observed_tc_k=None, measurement_floor_k=20.0), predicted_tc_k=17.0)
    cal = calibrate([conclusive, weak])
    assert cal.n == 1
    assert cal.inconclusive == 1


def test_calibration_detects_a_method_running_high():
    a = assess(ev(observed_tc_k=9.4), predicted_tc_k=17.0)
    cal = calibrate([a])
    assert cal.factor < 1.0
    assert 0 < cal.penalty <= MAX_CALIBRATION_PENALTY
    assert "high" in cal.describe()


def test_calibration_penalty_is_capped():
    a = assess(ev(observed_tc_k=0.5), predicted_tc_k=23.5)
    assert calibrate([a]).penalty == MAX_CALIBRATION_PENALTY


def test_no_evidence_means_no_penalty():
    cal = calibrate([])
    assert cal.factor is None and cal.penalty == 0.0


# --- the loop actually closes ----------------------------------------------

def test_evidence_changes_the_ranking():
    policy = WeightedPolicy.from_yaml(POLICY)
    evidence = load_evidence(EXAMPLE)
    before = {rc.candidate.formula: rc.rank for rc in rank(load(), policy)}
    after = {rc.candidate.formula: rc.rank
             for rc in rank(derive_metrics(load_candidates(), evidence=evidence), policy)}
    assert before != after, "evidence that changes nothing is not a loop"


def test_a_measured_candidate_uses_the_measurement_not_the_prediction():
    evidence = load_evidence(EXAMPLE)
    cands = {c.formula: c for c in derive_metrics(load_candidates(), evidence=evidence)}
    liz = cands["LiZrH6Ru"]
    assert liz.has_measured_tc
    assert liz.best_tc_k == 9.4
    assert liz.derivation["tc"]["method"] == "measured"
    # the predictions stay on the record so the size of the miss is not lost
    assert liz.tc_allen_dynes_k == 23.5 and liz.tc_refined_k == 17.0


def test_measurement_raises_confidence_above_any_calculation():
    evidence = load_evidence(EXAMPLE)
    cands = {c.formula: c for c in derive_metrics(load_candidates(), evidence=evidence)}
    measured = cands["LiZrH6Ru"].metrics["tc_confidence"]
    calculated = cands["EuCdH6Ru"].metrics["tc_confidence"]
    assert measured > calculated


def test_calibration_penalises_untested_candidates_of_the_same_method():
    """The whole point of method-level calibration: evidence about one compound
    should cost confidence in the twenty-one that rest on the same method."""
    evidence = load_evidence(EXAMPLE)
    without = {c.formula: c for c in load()}
    with_ev = {c.formula: c for c in derive_metrics(load_candidates(), evidence=evidence)}
    untested = "EuCdH6Ru"
    assert not with_ev[untested].has_measured_tc
    assert (with_ev[untested].metrics["tc_confidence"]
            < without[untested].metrics["tc_confidence"])


def test_predictions_are_never_silently_rewritten():
    """A calibration lowers confidence. It must not invent a corrected Tc."""
    evidence = load_evidence(EXAMPLE)
    with_ev = {c.formula: c for c in derive_metrics(load_candidates(), evidence=evidence)}
    untested = with_ev["EuCdH6Ru"]
    assert untested.best_tc_k == untested.tc_allen_dynes_k == 13.6
