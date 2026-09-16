"""Hydride Triage — a ranking you can argue with, live."""

from __future__ import annotations

import glob

import altair as alt
import pandas as pd
import streamlit as st

from policy.weighted_policy import WeightedPolicy
from triage.hydride_loader import load
from triage.ranking import consensus_shortlist, rank, sensitivity
from triage.validation_plan import build_workflow, hypothesis_for

METRICS = ["tc_score", "tc_confidence", "synthesis_feasibility", "information_value"]
METRIC_LABEL = {
    "tc_score": "Predicted Tc",
    "tc_confidence": "Confidence in that Tc",
    "synthesis_feasibility": "Synthesis feasibility",
    "information_value": "Information value",
}
METRIC_HELP = {
    "tc_score": "Best available Tc, normalized against the strongest candidate in this cohort.",
    "tc_confidence": "Derived from the coupling regime and whether a beyond-Allen-Dynes "
                     "calculation exists. Not published — see SOURCE.md.",
    "synthesis_feasibility": "Weakest-link score over the formula's elements, from an "
                             "analyst rule table. Judgment, not data.",
    "information_value": "High where a high predicted Tc rests on a weak estimate — "
                         "exactly what an experiment would resolve.",
}


@st.cache_data(ttl=60)
def _candidates():
    return load()


@st.cache_data(ttl=60)
def _preset_policies():
    return [WeightedPolicy.from_yaml(p)
            for p in sorted(glob.glob("configs/policies/hydride_*.yaml"))]


def render() -> None:
    st.subheader("Hydride Candidate Triage")

    try:
        candidates = _candidates()
        presets = _preset_policies()
    except Exception as e:
        st.error(f"Could not load the hydride dataset: {e}")
        return

    n_refined = sum(1 for c in candidates if c.has_refined_tc)
    st.caption(
        f"{len(candidates)} candidates transcribed verbatim from Sanna et al., "
        f"*Communications Physics* (2026). No physics is simulated: λ, ω_log and "
        f"Allen–Dynes Tc are published values; confidence and feasibility are derived "
        f"or analyst judgment, kept in separate files. See `datasets/hydrides/SOURCE.md`.")

    if n_refined < len(candidates):
        st.warning(
            f"**Only {n_refined} of {len(candidates)} candidates has a beyond-Allen–Dynes "
            f"Tc.** For that one, refinement moved 23.5 K → 17 K, which the authors call "
            f"\"an uncommon deviation\". Every other ranking below rests on a number the "
            f"paper's own authors caution against over-reading.")

    # ---------------- policy controls ----------------
    st.markdown("#### Decision policy")
    st.caption("Weights are a decision policy, not a physical constant. Move them and "
               "watch the ranking answer differently.")

    left, right = st.columns([1, 2])
    with left:
        preset_name = st.radio(
            "Start from", [p.name for p in presets] + ["Custom"], index=0,
            help="Presets are versioned files in configs/policies/.")
    base = next((p for p in presets if p.name == preset_name), presets[0])

    # Streamlit ignores a keyed widget's `value=` once session_state holds one,
    # so selecting a different preset would move the radio and leave the sliders
    # where they were. Push the new preset's weights into state BEFORE the
    # sliders are created — after that point the write is rejected.
    if st.session_state.get("_hydride_preset") != preset_name:
        st.session_state["_hydride_preset"] = preset_name
        if preset_name != "Custom":
            for m in METRICS:
                st.session_state[f"w_{m}"] = float(base.weights.get(m, 0.0))

    with right:
        raw: dict[str, float] = {}
        cols = st.columns(2)
        for i, m in enumerate(METRICS):
            cols[i % 2].slider(
                METRIC_LABEL[m], 0.0, 1.0, float(base.weights.get(m, 0.0)), 0.05,
                key=f"w_{m}", help=METRIC_HELP[m])
            raw[m] = st.session_state[f"w_{m}"]

    total = sum(raw.values())
    if total <= 0:
        st.error("All weights are zero — there is nothing to rank on. Raise at least one.")
        return

    # WeightedPolicy requires weights to sum to 1.0 so scores stay comparable
    # between policies. Sliders will not do that on their own, so normalize and
    # show the result rather than silently accepting an un-normalized sum.
    weights = {m: round(w / total, 6) for m, w in raw.items() if w > 0}
    weights[max(weights, key=weights.get)] += round(1.0 - sum(weights.values()), 6)
    changed = (preset_name == "Custom"
               or any(abs(raw[m] - base.weights.get(m, 0.0)) > 1e-6 for m in METRICS))

    policy = WeightedPolicy.from_dict({
        "policy_id": "custom_live" if changed else base.policy_id,
        "name": "Custom (live)" if changed else base.name,
        "weights": weights,
    }, source="dashboard")

    st.caption("Normalized weights in effect: " +
               " · ".join(f"**{METRIC_LABEL[m]}** {w:.0%}" for m, w in weights.items()))

    # ---------------- ranking ----------------
    ranked = rank(candidates, policy)
    rows = []
    for rc in ranked:
        c, d = rc.candidate, rc.candidate.derivation
        rows.append({
            "#": rc.rank, "Formula": c.formula, "Score": rc.score,
            "Tc (K)": c.best_tc_k,
            "Tc source": "refined" if c.has_refined_tc else "Allen–Dynes",
            "λ": c.lambda_ep,
            "Confidence": c.metrics["tc_confidence"],
            "Feasibility": c.metrics["synthesis_feasibility"],
            "Limited by": d["feasibility"]["limiting_element"],
            "Family": "double perovskite" if "perovskite" in c.structure_family else "fluorite-like",
        })
    df = pd.DataFrame(rows)

    st.markdown("#### Ranking")
    st.dataframe(
        df, hide_index=True, width="stretch", height=380,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0.0, max_value=1.0, format="%.3f"),
            "Feasibility": st.column_config.NumberColumn(format="%.2f"),
            "Confidence": st.column_config.NumberColumn(format="%.2f"),
            "Tc (K)": st.column_config.NumberColumn(format="%.1f"),
        })

    infeasible = df[df["Feasibility"] <= 0.1]
    if not infeasible.empty:
        st.error(
            f"**{len(infeasible)} of {len(df)} candidates contain technetium**, which has "
            f"no stable isotope and needs a licensed facility. That constraint is visible "
            f"from the formula alone and invisible in any Tc-ordered list — which is the "
            f"case for triage having a feasibility term at all.")

    # ---------------- sensitivity ----------------
    st.divider()
    st.markdown("#### Does the answer survive disagreement?")
    st.caption("Ranks under each preset policy. A candidate that only wins under one "
               "weighting is there because of a choice someone made, not because of data.")

    sens = sensitivity(candidates, presets)
    short = {p.policy_id: p.name for p in presets}
    srows = [{"Formula": r["formula"],
              **{short[pid]: rk for pid, rk in r["ranks"].items()},
              "Spread": r["rank_spread"], "Stability": r["stability"]}
             for r in sens]
    sdf = pd.DataFrame(srows)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.dataframe(sdf.head(12), hide_index=True, width="stretch")
    with c2:
        chart = alt.Chart(sdf.head(12)).mark_bar().encode(
            y=alt.Y("Formula:N", sort="-x", title=None),
            x=alt.X("Spread:Q", title="Rank spread across policies"),
            color=alt.Color("Stability:N",
                            scale=alt.Scale(domain=["stable", "moderate", "policy-driven"],
                                            range=["#15803d", "#b45309", "#c2410c"]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Formula", "Spread", "Stability"])
        st.altair_chart(chart.properties(height=330), use_container_width=True)

    consensus = consensus_shortlist(sens, top_n=5)
    if consensus:
        st.success(
            "**Consensus shortlist — top 5 under every policy: " +
            ", ".join(r["formula"] for r in consensus) + ".** "
            "This, not rank 1, is the useful output: these are worth validating "
            "regardless of whose priorities win the argument.")
    else:
        st.warning("No candidate holds a top-5 position under every policy. That is "
                   "itself the finding — this cohort has no policy-independent pick.")

    # ---------------- provenance + plan ----------------
    st.divider()
    st.markdown("#### Inspect a candidate")
    pick = st.selectbox("Candidate", [rc.candidate.formula for rc in ranked])
    rc = next(r for r in ranked if r.candidate.formula == pick)
    c, d = rc.candidate, rc.candidate.derivation

    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**Where each number comes from**")
        st.dataframe(pd.DataFrame([
            {"Quantity": "λ (electron–phonon coupling)", "Value": f"{c.lambda_ep:.2f}",
             "Provenance": "published — paper table"},
            {"Quantity": "ω_log", "Value": f"{c.omega_log_k:.2f} K",
             "Provenance": "published — paper table"},
            {"Quantity": "Allen–Dynes Tc", "Value": f"{c.tc_allen_dynes_k:.1f} K",
             "Provenance": "published — paper table"},
            {"Quantity": "Refined Tc",
             "Value": f"{c.tc_refined_k:.1f} K" if c.has_refined_tc else "not reported",
             "Provenance": "published" if c.has_refined_tc else "missing — not imputed"},
            {"Quantity": "Tc confidence", "Value": f"{c.metrics['tc_confidence']:.2f}",
             "Provenance": "derived — triage/derive.py"},
            {"Quantity": "Synthesis feasibility",
             "Value": f"{c.metrics['synthesis_feasibility']:.2f}",
             "Provenance": f"analyst rule — {d['feasibility']['rule_set_id']}"},
        ]), hide_index=True, width="stretch")
        st.caption(f"**Confidence rationale.** {d['confidence']['rationale']}")
        st.caption(f"**Feasibility limited by {d['feasibility']['limiting_element']}.** "
                   f"{d['feasibility']['reason']}")

    with p2:
        st.markdown("**Score composition under the current policy**")
        contrib = pd.DataFrame([
            {"Term": METRIC_LABEL[k], "Contribution": v}
            for k, v in rc.contributions.items()])
        st.altair_chart(
            alt.Chart(contrib).mark_bar(color="#1f5f8b").encode(
                y=alt.Y("Term:N", sort="-x", title=None),
                x=alt.X("Contribution:Q", scale=alt.Scale(domain=[0, 1])),
                tooltip=["Term", "Contribution"]).properties(height=170),
            use_container_width=True)
        st.metric("Total score", f"{rc.score:.3f}", help="Sum of the contributions above.")

    with st.expander(f"Validation plan and hypothesis for {c.formula}"):
        wf = build_workflow(rc, policy.policy_id)
        hyp = hypothesis_for(rc, policy.policy_id)
        st.markdown(f"**Claim.** {hyp['claim']}")
        st.markdown(f"**What this would settle.** {hyp['what_this_settles']}")
        st.markdown("**Caveats**")
        for cav in hyp["known_caveats"]:
            st.markdown(f"- {cav}")
        st.info(f"**Execution status: {wf['execution_status']['state']}.** "
                f"{wf['execution_status']['note']}")
        st.caption("The generated workflow is parsed by `orchestrator.workflow_parser` "
                   "and judged by `orchestrator.safety_gate` — the same modules the CdTe "
                   "loop uses, unchanged.")
        st.json({"parameters": wf["parameters"],
                 "safety": wf["safety"], "steps": wf["steps"]}, expanded=False)
