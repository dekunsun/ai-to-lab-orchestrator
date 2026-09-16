"""Command Center — what is the state of the lab right now."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from dashboard import data


def render() -> None:
    st.subheader("Command Center")
    st.caption("Everything on this page is read from `db/lab.sqlite`. "
               "The dashboard renders state; it never writes it.")

    exps = data.experiments()
    if exps.empty:
        data.empty_state(
            "experiments in the database",
            "./.venv/bin/python run_cdte_demo.py --budget 30 --seed 0")
        return

    completed = exps[exps["status"] == "completed"]
    failed = exps[exps["status"] == "failed"]
    blocked = exps[exps["status"] == "blocked"]
    eligible = exps[exps["included_in_optimizer"] == 1]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Experiments", len(exps))
    c2.metric("Best objective",
              f"{completed['objective_score'].max():.3f}" if not completed.empty else "—")
    c3.metric("Valid feedback", f"{len(eligible) / len(exps):.0%}",
              help="Completed AND clean enough to condition the optimizer. "
                   "Not every completed experiment qualifies.")
    c4.metric("Failed", len(failed), help="A sample was consumed and yielded nothing.")
    c5.metric("Blocked by gate", len(blocked),
              delta=f"{len(blocked)} samples saved" if len(blocked) else None,
              delta_color="normal",
              help="The safety gate refused to spend a sample. Zero devices ran.")

    st.divider()
    left, right = st.columns([3, 2])

    with left:
        st.markdown("**Recent experiments**")
        view = exps.head(12)[
            ["experiment_id", "method", "status", "objective_score",
             "data_quality_score", "failure_category", "policy_id"]].copy()
        view.columns = ["ID", "Proposed by", "Status", "Objective",
                        "Data quality", "Failure / block reason", "Scoring policy"]
        st.dataframe(view, hide_index=True, width="stretch")

    with right:
        st.markdown("**Safety gate verdicts**")
        breakdown = data.safety_breakdown(exps)
        if breakdown:
            label = {
                "approved": "Approved",
                "approved_with_flags": "Approved with flags",
                "blocked": "Blocked — hazard rule",
                "rejected": "Rejected — out of bounds",
            }
            rows = pd.DataFrame(
                [{"Verdict": label.get(k, k), "Count": v} for k, v in breakdown.items()]
            ).sort_values("Count", ascending=False)
            st.dataframe(rows, hide_index=True, width="stretch")
            if breakdown.get("blocked"):
                st.caption(
                    f"{breakdown['blocked']} proposal(s) were withheld before any device "
                    "ran. A block prevents a sample from being burned; a failure means "
                    "one already was.")
        else:
            st.caption("No safety reviews recorded.")

        if not failed.empty:
            st.markdown("**Failure taxonomy**")
            tax = (failed["failure_category"].value_counts()
                   .rename_axis("Category").reset_index(name="Count"))
            st.dataframe(tax, hide_index=True, width="stretch")

    st.divider()
    st.markdown("**Hypothesis registry**")
    hyps = data.hypotheses()
    if hyps.empty:
        data.empty_state("registered hypotheses",
                         "./.venv/bin/python scripts/run_hydride_triage.py")
        return

    st.caption("A triage decision that produces only a ranked table leaves no record "
               "of its reasoning. These entries can later be marked supported or "
               "contradicted by evidence.")
    for _, row in hyps.iterrows():
        with st.expander(f"{row['hypothesis_id']} · {row['subject']} · {row['status']}"):
            st.markdown(f"**Claim.** {row['claim']}")
            st.markdown(f"**What this would settle.** {row['what_this_settles']}")
            try:
                detail = json.loads(row["detail_json"])
            except Exception:
                detail = {}
            if detail.get("known_caveats"):
                st.markdown("**Caveats**")
                for c in detail["known_caveats"]:
                    st.markdown(f"- {c}")
            if detail.get("why_negative_is_useful"):
                st.markdown(f"**Why a negative result still pays.** "
                            f"{detail['why_negative_is_useful']}")
            st.caption(f"Selected by policy `{row['selected_by_policy']}` "
                       f"at rank {row['rank_under_policy']} · source `{row['source']}`")
