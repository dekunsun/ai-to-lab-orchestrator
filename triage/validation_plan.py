"""Turn a triage decision into something the orchestrator can actually run.

This is the join between the two halves of the project. Triage does not end at
a ranked table: the selected candidate becomes a workflow specification and a
hypothesis, both of which enter the SAME machinery the CdTe loop uses — the
same YAML schema, the same parser, the same safety gate.

What this deliberately does NOT do is simulate hydride synthesis. There are no
hydride devices in this repository and there will not be fabricated ones; a
made-up synthesis model would be exactly the fake physics the project refuses
elsewhere. The plan is generated, schema-validated and safety-reviewed, and
then it stops at the point where real instruments would take over. The seam is
where a real lab's seam is.
"""

from __future__ import annotations

import os
from typing import Any

import yaml

from triage.ranking import RankedCandidate

# Ranges a hydride synthesis campaign would plausibly sweep. These bound the
# generated workflow so the safety gate has something real to check; they are
# process envelope, not a claim about where the optimum sits.
SYNTHESIS_PARAMETERS = {
    "anneal_temp_c": {"type": "float", "min": 300.0, "max": 900.0},
    "anneal_time_h": {"type": "float", "min": 1.0, "max": 72.0},
    "h2_pressure_bar": {"type": "float", "min": 1.0, "max": 200.0},
}

HAZARD_RULES = [
    {
        "name": "hydrogen_pressure_at_temperature",
        # Hot plus high-pressure hydrogen is the combination that matters here:
        # each bound is individually acceptable, together they are a hydrogen
        # embrittlement and vessel-rupture concern.
        "condition": "h2_pressure_bar > 120 and anneal_temp_c > 700",
        "risk_level": "high",
        "action": "block",
    },
    {
        "name": "extended_high_pressure_hold",
        "condition": "h2_pressure_bar > 150 and anneal_time_h > 48",
        "risk_level": "medium",
        "action": "flag",
    },
]


def hypothesis_for(rc: RankedCandidate, policy_id: str) -> dict[str, Any]:
    """State what validating this candidate would actually settle."""
    c = rc.candidate
    tc = c.derivation["tc"]
    conf = c.derivation["confidence"]

    if c.has_refined_tc:
        claim = (f"{c.formula} superconducts near {c.tc_refined_k:g} K at ambient "
                 f"pressure, as estimated by {c.tc_refined_method}.")
        settles = (f"Whether the refined estimate ({c.tc_refined_k:g} K) or the "
                   f"Allen-Dynes value ({c.tc_allen_dynes_k:g} K) is closer to "
                   "measurement. The two disagree by "
                   f"{abs(tc['delta_vs_allen_dynes']):g} K.")
    else:
        claim = (f"{c.formula} superconducts near {c.tc_allen_dynes_k:g} K at "
                 "ambient pressure, as estimated by the Allen-Dynes formula.")
        settles = ("Whether an unrefined Allen-Dynes estimate holds up for this "
                   f"coupling regime ({conf['rationale'].split(';')[0].strip()}).")

    return {
        "hypothesis_id": f"HYP-{c.candidate_id}",
        "subject": c.formula,
        "mat_id": c.mat_id,
        "claim": claim,
        "what_this_settles": settles,
        "status": "proposed",
        "selected_by_policy": policy_id,
        "rank_under_policy": rc.rank,
        "negative_result_is_useful": True,
        "why_negative_is_useful": (
            "A measured Tc well below the prediction is direct evidence on where "
            "these estimates break down, and this cohort rests almost entirely on "
            "unrefined Allen-Dynes values — so the correction generalizes beyond "
            "this one compound."),
        "known_caveats": [
            conf["rationale"],
            f"synthesis limited by {c.derivation['feasibility']['limiting_element']}: "
            f"{c.derivation['feasibility']['reason']}",
        ],
    }


def build_workflow(rc: RankedCandidate, policy_id: str) -> dict[str, Any]:
    """Emit a workflow YAML body for synthesizing and characterizing a candidate."""
    c = rc.candidate
    return {
        "workflow_id": f"hydride_validation_{c.formula.lower()}_v1",
        "project": "hydride_candidate_validation",
        "objective": {
            "name": "confirm_ambient_pressure_superconductivity",
            "metrics": ["phase_fraction", "resistivity_drop_k",
                        "magnetic_susceptibility_onset_k"],
        },
        "parameters": SYNTHESIS_PARAMETERS,
        "safety": {"hazard_rules": HAZARD_RULES},
        "steps": [
            {"name": "weigh_and_mix_precursors", "device": "powder_dispenser"},
            {"name": "hydrogenation_anneal", "device": "hydrogenation_furnace"},
            {"name": "confirm_phase", "device": "xrd_instrument"},
            {"name": "resistivity_vs_temperature", "device": "ppms_resistivity"},
            {"name": "magnetic_susceptibility", "device": "squid_magnetometer"},
            {"name": "compute_objective", "device": "scoring_engine"},
        ],
        "provenance": {
            "selected_from": "datasets/hydrides/gnome_hydride_candidates.csv",
            "candidate_id": c.candidate_id,
            "mat_id": c.mat_id,
            "selected_by_policy": policy_id,
            "rank_under_policy": rc.rank,
            "policy_score": rc.score,
        },
        "execution_status": {
            "state": "awaiting_device_implementation",
            "note": ("No hydride synthesis devices exist in this repository. "
                     "This workflow is generated, schema-validated and "
                     "safety-reviewed, but not executed — simulating hydride "
                     "synthesis would be the fake physics this project avoids."),
        },
    }


def write_plan(rc: RankedCandidate, policy_id: str,
               out_dir: str = "configs/workflows/generated") -> str:
    os.makedirs(out_dir, exist_ok=True)
    wf = build_workflow(rc, policy_id)
    path = os.path.join(out_dir, f"{wf['workflow_id']}.yaml")
    header = (
        "# GENERATED by triage/validation_plan.py — do not edit by hand.\n"
        f"# Candidate {rc.candidate.formula} ({rc.candidate.mat_id}), "
        f"rank {rc.rank} under policy {policy_id}.\n"
        "# Published source: datasets/hydrides/SOURCE.md\n\n")
    with open(path, "w") as f:
        f.write(header)
        yaml.safe_dump(wf, f, sort_keys=False, default_flow_style=False)
    return path
