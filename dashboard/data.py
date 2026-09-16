"""Read-only access to persisted state for the dashboard.

The dashboard visualizes state; it does not own workflow logic. Every function
here reads something another part of the system wrote — the SQLite database, a
benchmark JSON, the published hydride table. Nothing here decides anything.

That separation is the point. A Streamlit app that starts orchestrating becomes
the system's brain by accident, and then the orchestration logic is trapped
inside a UI that cannot be tested or run headless.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

import pandas as pd
import streamlit as st

DB_PATH = "db/lab.sqlite"
BENCHMARK_DIR = "artifacts/benchmark_results"


def _connect() -> sqlite3.Connection | None:
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data(ttl=5)
def experiments() -> pd.DataFrame:
    conn = _connect()
    if conn is None:
        return pd.DataFrame()
    try:
        return pd.read_sql_query(
            "SELECT * FROM experiments ORDER BY rowid DESC", conn)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=5)
def steps() -> pd.DataFrame:
    conn = _connect()
    if conn is None:
        return pd.DataFrame()
    try:
        return pd.read_sql_query("SELECT * FROM workflow_steps", conn)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=5)
def hypotheses() -> pd.DataFrame:
    conn = _connect()
    if conn is None:
        return pd.DataFrame()
    try:
        return pd.read_sql_query(
            "SELECT * FROM hypotheses ORDER BY created_at DESC", conn)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=30)
def benchmark(policy_id: str = "cdte_balanced_device_quality") -> dict[str, Any] | None:
    suffix = "" if policy_id == "cdte_balanced_device_quality" else f"_{policy_id}"
    path = os.path.join(BENCHMARK_DIR, f"cdte_benchmark{suffix}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


@st.cache_data(ttl=30)
def available_benchmarks() -> dict[str, str]:
    """Map policy_id -> file, for every benchmark that has actually been run."""
    out = {}
    if not os.path.isdir(BENCHMARK_DIR):
        return out
    for name in sorted(os.listdir(BENCHMARK_DIR)):
        if name.startswith("cdte_benchmark") and name.endswith(".json"):
            with open(os.path.join(BENCHMARK_DIR, name)) as f:
                data = json.load(f)
            pid = data.get("policy", {}).get("policy_id", "unknown")
            out[pid] = name
    return out


def safety_breakdown(df: pd.DataFrame) -> dict[str, int]:
    """Count gate verdicts. Stored as JSON, so it is parsed rather than queried."""
    counts: dict[str, int] = {}
    for raw in df.get("safety_json", []):
        try:
            status = json.loads(raw).get("approval_status", "unknown")
        except Exception:
            status = "unparseable"
        counts[status] = counts.get(status, 0) + 1
    return counts


def empty_state(what: str, command: str) -> None:
    """Tell the reader how to produce the missing data, not just that it is missing."""
    st.info(f"No {what} yet. Generate it with:")
    st.code(command, language="bash")
