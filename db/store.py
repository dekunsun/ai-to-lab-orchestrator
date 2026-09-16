"""Minimal SQLite persistence for experiment records.

The DB is the system's memory. For Phase 1 we persist the three tables that
matter for the closed loop and the experiment trace:
    experiments, workflow_steps, artifacts
Later phases extend this with hypotheses, safety_reviews, model_feedback.
"""

from __future__ import annotations
import json
import sqlite3
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    workflow_id TEXT,
    project TEXT,
    method TEXT,                  -- which optimizer proposed it
    run_seed INTEGER,             -- benchmark seed, for reproducibility
    parameters_json TEXT,
    status TEXT,
    objective_score REAL,
    data_quality_score REAL,
    failure_category TEXT,
    included_in_optimizer INTEGER,
    policy_id TEXT,            -- which decision policy produced objective_score
    safety_json TEXT
);
CREATE TABLE IF NOT EXISTS workflow_steps (
    step_pk INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT,
    step_name TEXT,
    device TEXT,
    status TEXT,
    outputs_json TEXT,
    data_quality_score REAL,
    failure_category TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_pk INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT,
    step_name TEXT,
    artifact_type TEXT,
    artifact_json TEXT
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after a database was first created.

    `CREATE TABLE IF NOT EXISTS` silently does nothing on an existing table, so
    a schema change would otherwise fail at INSERT time against an older
    db/lab.sqlite. Cheap to handle now; painful to debug later.
    """
    have = {row[1] for row in conn.execute("PRAGMA table_info(experiments)")}
    for column, ddl in [("policy_id", "ALTER TABLE experiments ADD COLUMN policy_id TEXT")]:
        if column not in have:
            conn.execute(ddl)


def connect(path: str = "db/lab.sqlite") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn


def save_experiment(conn: sqlite3.Connection, record: dict[str, Any],
                    method: str, run_seed: int) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO experiments
           (experiment_id, workflow_id, project, method, run_seed, parameters_json,
            status, objective_score, data_quality_score, failure_category,
            included_in_optimizer, policy_id, safety_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (record["experiment_id"], record["workflow_id"], record["project"],
         method, run_seed, json.dumps(record["parameters"]),
         record["status"], record["objective_score"], record["data_quality_score"],
         record["failure_category"], int(record["included_in_optimizer"]),
         record.get("policy_id"), json.dumps(record["safety_review"])),
    )
    for s in record["steps"]:
        conn.execute(
            """INSERT INTO workflow_steps
               (experiment_id, step_name, device, status, outputs_json,
                data_quality_score, failure_category)
               VALUES (?,?,?,?,?,?,?)""",
            (record["experiment_id"], s["step"], s["device"], s["status"],
             json.dumps(s.get("outputs", {})), s.get("data_quality_score"),
             s.get("failure_category")),
        )
    for a in record["artifacts"]:
        conn.execute(
            """INSERT INTO artifacts
               (experiment_id, step_name, artifact_type, artifact_json)
               VALUES (?,?,?,?)""",
            (a["experiment_id"], a.get("step"), a.get("artifact_type"), json.dumps(a)),
        )
    conn.commit()
