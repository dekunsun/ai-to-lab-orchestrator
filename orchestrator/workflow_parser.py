"""Load and lightly validate a workflow YAML into a typed object."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import yaml


@dataclass
class Workflow:
    workflow_id: str
    project: str
    objective: dict[str, Any]
    parameters: dict[str, dict[str, Any]]
    steps: list[dict[str, str]]
    safety: dict[str, Any]
    raw: dict[str, Any]

    def param_bounds(self) -> dict[str, tuple[float, float]]:
        return {k: (float(v["min"]), float(v["max"])) for k, v in self.parameters.items()}

    def device_sequence(self) -> list[str]:
        return [s["device"] for s in self.steps]


def load_workflow(path: str) -> Workflow:
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    required = ["workflow_id", "project", "objective", "parameters", "steps"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"workflow {path} missing keys: {missing}")

    for pname, spec in data["parameters"].items():
        if "min" not in spec or "max" not in spec:
            raise ValueError(f"parameter {pname} needs min and max")
        if spec["min"] >= spec["max"]:
            raise ValueError(f"parameter {pname}: min must be < max")

    return Workflow(
        workflow_id=data["workflow_id"],
        project=data["project"],
        objective=data["objective"],
        parameters=data["parameters"],
        steps=data["steps"],
        safety=data.get("safety", {}),
        raw=data,
    )
