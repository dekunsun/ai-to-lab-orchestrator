"""Workflow executor — the orchestration core.

Given a parsed Workflow, a device registry, and a set of proposed parameters,
it runs the steps in order and returns ONE structured experiment record:

    {
      experiment_id, workflow_id, project, parameters,
      status: completed | failed | blocked,
      objective_score: float | None,
      safety_review: {...},
      steps: [ {step, device, status, outputs, ...}, ... ],
      measurements: { flattened device outputs },
      artifacts: [ ... ],
      data_quality_score, failure_category, included_in_optimizer, policy_id
    }

This record is the unit the DB layer persists and the optimizer consumes.
"""

from __future__ import annotations
import uuid
from typing import Any

from orchestrator.workflow_parser import Workflow
from orchestrator import safety_gate
from devices.base import BaseDevice


# A result is only fed back to the optimizer if it succeeded AND its data is
# clean enough. This threshold is where "data quality gates model feedback".
MIN_DATA_QUALITY_FOR_FEEDBACK = 0.5


def _new_experiment_id() -> str:
    return "EXP-" + uuid.uuid4().hex[:8]


def execute_workflow(
    workflow: Workflow,
    devices: dict[str, BaseDevice],
    parameters: dict[str, float],
) -> dict[str, Any]:
    exp_id = _new_experiment_id()
    record: dict[str, Any] = {
        "experiment_id": exp_id,
        "workflow_id": workflow.workflow_id,
        "project": workflow.project,
        "parameters": dict(parameters),
        "status": "completed",
        "objective_score": None,
        "safety_review": None,
        "steps": [],
        "measurements": {},
        "artifacts": [],
        "data_quality_score": 1.0,
        "failure_category": None,
        "included_in_optimizer": False,
        "policy_id": None,
    }

    # --- safety gate: runs BEFORE any device is touched ---
    # A blocked experiment consumes zero lab time. That is the entire value of
    # the gate, and it is why "blocked" is a distinct status from "failed":
    # a failure burned a sample, a block prevented one from being burned.
    review = safety_gate.review_parameters(workflow, parameters)
    record["safety_review"] = review
    if review["approval_status"] in ("rejected", "blocked"):
        record["status"] = "blocked"
        record["failure_category"] = review["blocked_by"]
        record["data_quality_score"] = 0.0
        return record

    # --- run steps in order, threading accumulated measurements downstream ---
    upstream: dict[str, Any] = {}
    quality_scores: list[float] = []

    for step in workflow.steps:
        step_name = step["name"]
        device_name = step["device"]
        device = devices.get(device_name)
        if device is None:
            record["status"] = "failed"
            record["failure_category"] = "unknown_device"
            record["steps"].append({"step": step_name, "device": device_name,
                                     "status": "failed", "reason": "device_not_registered"})
            return record

        result = device.run({"parameters": parameters, "upstream": upstream})
        quality_scores.append(result["data_quality_score"])

        record["steps"].append({
            "step": step_name,
            "device": device_name,
            "status": result["status"],
            "outputs": result["outputs"],
            "metadata": result["metadata"],
            "data_quality_score": result["data_quality_score"],
            "failure_category": result["failure_category"],
        })

        if result["artifacts"]:
            for a in result["artifacts"]:
                record["artifacts"].append({"experiment_id": exp_id, "step": step_name, **a})

        if result["status"] == "failed":
            # failure short-circuits the workflow — this is first-class data
            record["status"] = "failed"
            record["failure_category"] = result["failure_category"]
            record["data_quality_score"] = round(min(quality_scores), 4)
            return record

        # accumulate this step's measurements for downstream devices
        upstream.update(result["outputs"])

    # --- success: aggregate ---
    # Capture the decision policy that produced the objective. Provenance is not
    # only about how data was measured — it is also about which trade-off was
    # applied to turn that data into a decision.
    for s_ in record["steps"]:
        pid = (s_.get("metadata") or {}).get("policy_id")
        if pid:
            record["policy_id"] = pid

    record["measurements"] = dict(upstream)
    record["objective_score"] = upstream.get("objective_score")
    record["data_quality_score"] = round(min(quality_scores), 4) if quality_scores else 1.0
    record["included_in_optimizer"] = (
        record["objective_score"] is not None
        and record["data_quality_score"] >= MIN_DATA_QUALITY_FOR_FEEDBACK
    )
    return record
