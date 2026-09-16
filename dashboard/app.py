"""AI-to-Lab Orchestrator — dashboard entry point.

    ./.venv/bin/streamlit run dashboard/app.py

Three views, one principle: this app renders persisted state and recomputes
cheap derivations. It does not execute experiments, does not own workflow logic,
and writes nothing. Orchestration lives in orchestrator/, decisions in policy/
and triage/, and both are runnable headless without importing Streamlit.
"""

from __future__ import annotations

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="AI-to-Lab Orchestrator",
                   page_icon="🔬", layout="wide")

from dashboard.views import cdte_benchmark, command_center, hydride_triage  # noqa: E402

VIEWS = {
    "Command Center": command_center.render,
    "CdTe Benchmark": cdte_benchmark.render,
    "Hydride Triage": hydride_triage.render,
}


def main() -> None:
    # Deep-linkable views: ?view=Hydride+Triage opens straight to that tab, so a
    # view can be shared or bookmarked rather than described ("click the third one").
    names = list(VIEWS)
    requested = st.query_params.get("view")
    default = names.index(requested) if requested in names else 0

    with st.sidebar:
        st.title("AI-to-Lab Orchestrator")
        st.caption("A self-driving-lab orchestration prototype for materials discovery.")
        choice = st.radio("View", names, index=default, label_visibility="collapsed")
    if choice != requested:
        st.query_params["view"] = choice
        st.divider()
        st.markdown("**Scientific modeling scope**")
        st.caption(
            "The CdTe module is a literature-inspired noisy surrogate benchmark "
            "environment, not a physical simulator, and makes no claim about real "
            "device performance.\n\n"
            "The hydride module simulates no physics at all. It uses published values "
            "from Sanna et al., *Communications Physics* (2026) and builds triage and "
            "validation planning on top of them.")
        st.divider()
        st.caption("Renders state from `db/lab.sqlite` and `artifacts/`. "
                   "This app never writes.")

    VIEWS[choice]()


main()
