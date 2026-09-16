"""CdTe Benchmark — did the closed loop actually beat the baseline, and by how much."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from dashboard import data

METHOD_LABEL = {"bayesian_optimization": "Bayesian optimization",
                "random_search": "Random search"}
METHOD_COLOR = {"Bayesian optimization": "#1f5f8b", "Random search": "#8c8c8c"}


def _curves(results: dict, budget: int) -> pd.DataFrame:
    rows = []
    for method, r in results.items():
        label = METHOD_LABEL.get(method, method)
        for i in range(budget):
            rows.append({"Experiment": i + 1, "Method": label,
                         "Best found": r["curve_median"][i],
                         "q1": r["curve_q1"][i], "q3": r["curve_q3"][i]})
    return pd.DataFrame(rows)


def render() -> None:
    st.subheader("CdTe Benchmark")

    runs = data.available_benchmarks()
    if not runs:
        data.empty_state(
            "benchmark results",
            "./.venv/bin/python scripts/run_cdte_benchmark.py --seeds 30 --budget 30")
        return

    policy_id = st.selectbox(
        "Scoring policy", list(runs),
        format_func=lambda p: p.replace("cdte_", "").replace("_", " ").title(),
        help="Each policy defines a different objective. Scores are NOT comparable "
             "between policies — only operating points are.")
    payload = data.benchmark(policy_id)
    if payload is None:
        st.warning("Could not read that benchmark file.")
        return

    results, budget, seeds = payload["results"], payload["budget"], payload["seeds"]
    ceiling = payload.get("surrogate_ceiling", 0.897)

    st.caption(f"{seeds} seeds × {budget} experiments · policy "
               f"`{payload['policy']['policy_id']}` · generated {payload['generated_at']}")

    cols = st.columns(len(results) + 1)
    for col, (method, r) in zip(cols, results.items()):
        s = r["final_best"]
        col.metric(METHOD_LABEL.get(method, method), f"{s['median']:.3f}",
                   help=f"IQR [{s['q1']:.3f}, {s['q3']:.3f}] · "
                        f"failure {r['mean_failure_rate']:.0%} · "
                        f"blocked {r['mean_blocked_rate']:.0%}")
    if payload.get("paired"):
        p = payload["paired"]
        cols[-1].metric("BO wins", f"{p['a_wins']}/{p['n']} seeds",
                        delta=f"{p['median_gap']:+.3f} median gap",
                        help="Paired comparison is valid because both methods draw the "
                             "same per-experiment lab noise (common random numbers).")

    df = _curves(results, budget)
    order = [METHOD_LABEL.get(m, m) for m in results]
    colors = [METHOD_COLOR.get(m, "#666") for m in order]
    scale = alt.Scale(domain=order, range=colors)

    band = alt.Chart(df).mark_area(opacity=0.16).encode(
        x=alt.X("Experiment:Q", title="Experiments run (fixed budget)"),
        y=alt.Y("q1:Q", title="Best objective found so far"),
        y2="q3:Q",
        color=alt.Color("Method:N", scale=scale, legend=alt.Legend(orient="bottom")))
    line = alt.Chart(df).mark_line(strokeWidth=2.5).encode(
        x="Experiment:Q", y="Best found:Q",
        color=alt.Color("Method:N", scale=scale),
        tooltip=["Method", "Experiment", "Best found", "q1", "q3"])
    rule = alt.Chart(pd.DataFrame({"y": [ceiling]})).mark_rule(
        strokeDash=[5, 4], color="#888").encode(y="y:Q")

    st.altair_chart((band + line + rule).properties(height=380), use_container_width=True)

    st.markdown("#### How to read this honestly")
    a, b, c = st.columns(3)
    a.info("**The bands overlap.** BO wins in the median and on most seeds, but does "
           "not dominate. On a 5-dimensional landscape with a 30-experiment budget, "
           "clean separation would suggest the benchmark was too easy.")
    b.info("**BO is behind early.** It runs an initial design first, so it trails "
           "random search for roughly the first 10 experiments. The advantage is "
           "sample efficiency later in the budget, not from experiment one.")
    c.info(f"**Runs exceed the {ceiling:.3f} ceiling.** That line is the noise-free "
           "maximum; reported scores are noisy observations, so best-found is an "
           "optimistically biased estimator. Taking a max over noisy draws captures luck.")

    st.divider()
    st.markdown("#### Where each policy steers the process")
    st.caption("Same optimizer, same surrogate — only the objective differs. "
               "Median operating point across seeds.")

    rows = []
    for pid in runs:
        pay = data.benchmark(pid)
        if not pay:
            continue
        r = pay["results"].get("bayesian_optimization")
        if not r or not r.get("median_best_params"):
            continue
        rows.append({"Policy": pid.replace("cdte_", "").replace("_", " ").title(),
                     "Median best": r["final_best"]["median"],
                     **{k.replace("cdcl2_", "").replace("_", " "): v
                        for k, v in r["median_best_params"].items()}})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.warning("**Median-best is not comparable across rows.** Each policy defines "
                   "a different objective, so a higher number does not mean a better "
                   "process. The comparable quantity is the operating point: "
                   "manufacturability-first converges on a shorter treatment and "
                   "lighter doping — a visibly more conservative process.")
