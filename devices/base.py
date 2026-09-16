"""Base interface shared by all virtual lab devices.

Every device — whether it simulates deposition, a CdCl2 anneal, or an XRD
measurement — exposes the same `run(inputs) -> dict` contract. This uniformity
is what lets the orchestrator treat the lab as a sequence of interchangeable
modules (the "workcell" idea from real self-driving-lab software) instead of
hard-coding each instrument.

A device NEVER raises on a "scientific" failure (e.g. a degraded sample). It
returns a structured result with status="failed" so the failure becomes
first-class data the system can log, categorize, and learn from. It only raises
on genuine programming errors (bad inputs the caller should have caught).
"""

from __future__ import annotations
from typing import Any


# Canonical result schema returned by every device.
# Keeping this in one place means the executor and DB layer can rely on it.
def device_result(
    status: str,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    data_quality_score: float = 1.0,
    failure_category: str | None = None,
) -> dict[str, Any]:
    assert status in ("completed", "failed"), f"bad status: {status}"
    return {
        "status": status,
        "outputs": outputs or {},
        "metadata": metadata or {},
        "artifacts": artifacts or [],
        "data_quality_score": round(float(data_quality_score), 4),
        "failure_category": failure_category,
    }


class BaseDevice:
    """All virtual devices subclass this and implement `run`."""

    # Human-readable id used in workflow YAML (`device: <name>`).
    name: str = "base_device"

    def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
