"""Lightweight safety / human-approval gate.

Deliberately NOT a chemical-safety model. It demonstrates the principle that an
autonomous lab must pass every proposed parameter set through:

    bounds validation  ->  hazard rules  ->  risk level  ->  block or approve

Two things this gate is designed to make visible:

1. Bounds checking only catches "out of range". The hazard rules catch
   *combinations* that are each individually in-range but jointly risky — which
   is exactly where an optimizer's or an LLM's suggestion is valid-looking yet
   unsafe. Only the hazard layer can see that.

2. A governance layer that cannot WITHHOLD lab time is decoration. Rules carry
   an explicit `action`: `block` stops the experiment before any device runs;
   `flag` records the risk and lets it proceed under review. Blocked proposals
   are fed back to the optimizer as infeasible, so the safety policy actively
   shapes the search space rather than just annotating it afterwards.
"""

from __future__ import annotations
from typing import Any
from orchestrator.workflow_parser import Workflow


def _safe_eval_condition(condition: str, params: dict[str, float]) -> bool:
    """Evaluate a hazard condition string against parameter values.

    The eval namespace is restricted to the parameter names plus a couple of
    builtins, so a YAML-authored condition cannot run arbitrary code.
    """
    allowed = dict(params)
    allowed.update({"__builtins__": {}, "abs": abs, "min": min, "max": max})
    try:
        return bool(eval(condition, allowed))  # noqa: S307 - sandboxed namespace
    except Exception:
        # A malformed rule must fail safe (treat as triggered), not crash.
        return True


def review_parameters(workflow: Workflow, params: dict[str, float]) -> dict[str, Any]:
    """Return a safety review verdict for one proposed parameter set."""
    bounds = workflow.param_bounds()

    # --- 1. bounds / completeness check -------------------------------------
    out_of_bounds = []
    for name, (lo, hi) in bounds.items():
        if name not in params:
            out_of_bounds.append({"param": name, "issue": "missing"})
        elif not (lo <= params[name] <= hi):
            out_of_bounds.append({"param": name, "value": params[name], "bounds": [lo, hi]})

    if out_of_bounds:
        return {
            "risk_level": "high",
            "approval_status": "rejected",
            "blocked_by": "out_of_bounds",
            "blocked_reason": f"parameter(s) out of bounds: {out_of_bounds}",
            "hazard_flags": [],
        }

    # --- 2. hazard rules (in-range but jointly risky combinations) ----------
    blocking, flags = [], []
    for rule in workflow.safety.get("hazard_rules", []):
        if not _safe_eval_condition(rule["condition"], params):
            continue
        entry = {
            "name": rule["name"],
            "risk_level": rule.get("risk_level", "medium"),
            "action": rule.get("action", "flag"),
            "condition": rule["condition"],
        }
        (blocking if entry["action"] == "block" else flags).append(entry)

    if blocking:
        return {
            "risk_level": "high",
            "approval_status": "blocked",
            "blocked_by": blocking[0]["name"],
            "blocked_reason": (
                f"hazard rule '{blocking[0]['name']}' triggered "
                f"({blocking[0]['condition']}) — experiment withheld pending human approval"
            ),
            "hazard_flags": blocking + flags,
        }

    if flags:
        max_risk = "high" if any(f["risk_level"] == "high" for f in flags) else "medium"
        return {
            "risk_level": max_risk,
            # Proceeds, but the risk is recorded against the experiment so it is
            # visible in the trace and in the governance view.
            "approval_status": "approved_with_flags",
            "blocked_by": None,
            "blocked_reason": None,
            "hazard_flags": flags,
        }

    return {"risk_level": "low", "approval_status": "approved",
            "blocked_by": None, "blocked_reason": None, "hazard_flags": []}
