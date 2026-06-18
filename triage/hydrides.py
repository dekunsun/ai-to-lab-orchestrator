"""Hydride candidate triage — built on REAL published data.

This module loads the 25 hydride superconductors from the GNoME screening paper
(Table 1 + Table 2) and ranks them for experimental validation. It does NOT
simulate any physics: every Tc / lambda / omega_log value comes straight from
the published computational results. We only build decision support on top.
"""

import pandas as pd


def load_hydrides(path="configs/data/hydrides.csv"):
    """Load the published hydride data into a pandas DataFrame."""
    # comment="#" tells pandas to skip the source-attribution lines at the top
    df = pd.read_csv(path, comment="#")
    return df

def add_scores(df):
    """Add normalized 0..1 scoring dimensions used by triage policies.

    Every score is derived ONLY from the published values (Tc, lambda, omega_log).
    These are decision-support dimensions, not new physics.
    """
    df = df.copy()  # don't modify the original

    # Tc score: higher Tc is better. Normalize to [0,1] by the max Tc.
    # TASK: fill this in. Hint: df["tc_allen_dynes"] / df["tc_allen_dynes"].max()
    df["tc_score"] = df["tc_allen_dynes"] / df["tc_allen_dynes"].max()

    # Coupling score: normalize lambda to [0,1] by the max lambda.
    df["coupling_score"] = df["lambda"] / df["lambda"].max()

    # Synthesizability proxy: the paper notes very high Tc often comes with
    # thermodynamic instability (harder to synthesize). As a simple, honest
    # proxy, we PENALIZE extreme Tc — moderate-Tc candidates score higher here.
    # (This is a transparent heuristic, not a physical prediction.)
    max_tc = df["tc_allen_dynes"].max()
    df["synthesizability_proxy"] = 1.0 - (df["tc_allen_dynes"] / max_tc)

    return df

# Named decision policies. Each is a set of weights over the scoring dimensions.
# These are POLICY CHOICES, not scientific constants — different priorities give
# different rankings, and the system makes that explicit.
POLICIES = {
    "max_tc": {
        # chase the highest critical temperature, ignore everything else
        "tc_score": 1.0,
        "coupling_score": 0.0,
        "synthesizability_proxy": 0.0,
    },
    "lab_feasible_first": {
        # prioritize what we can likely actually synthesize and validate
        "tc_score": 0.2,
        "coupling_score": 0.2,
        "synthesizability_proxy": 0.6,
    },
    "balanced": {
        # a compromise across all three
        "tc_score": 0.4,
        "coupling_score": 0.3,
        "synthesizability_proxy": 0.3,
    },
}


def rank_by_policy(df, policy_name):
    """Score and rank all candidates under a named policy.

    Returns the DataFrame sorted best-first, with a 'priority' column.
    """
    weights = POLICIES[policy_name]

    df = add_scores(df)

    # priority = weighted sum of the scoring dimensions
    # TASK: fill in the weighted sum.
    # Hint: weights["tc_score"] * df["tc_score"]  +  ... for the other two.
    df["priority"] = (
        weights["tc_score"] * df["tc_score"] +
        weights["coupling_score"] * df["coupling_score"] +
        weights["synthesizability_proxy"] * df["synthesizability_proxy"]
    )

    # sort best-first
    df = df.sort_values("priority", ascending=False).reset_index(drop=True)
    return df

def make_validation_plan(df, policy_name, top_n=3):
    """Generate a human-readable validation plan for the top-N candidates.

    Each recommendation is grounded in the published data and the chosen policy —
    it explains WHAT to prioritize and WHY, including honest caveats.
    """
    ranked = rank_by_policy(df, policy_name)
    top = ranked.head(top_n)

    lines = [f"Validation plan (policy: {policy_name}, top {top_n} candidates)", ""]

    for i, row in top.iterrows():
        formula = row["formula"]
        tc = row["tc_allen_dynes"]
        synth = row["synthesizability_proxy"]

        # Build an honest, data-grounded caveat based on this candidate's profile.
        if synth < 0.2:
            caveat = ("very high Tc but low synthesizability proxy — confirm "
                      "thermodynamic stability BEFORE committing synthesis effort")
        elif synth > 0.6:
            caveat = ("modest Tc but high synthesizability proxy — a lower-risk "
                      "candidate, good for an early reliable validation")
        else:
            caveat = "balanced profile — reasonable trade-off of Tc and feasibility"

        # rank is i+1 because iterrows gives 0-based index on the sorted frame
        lines.append(f"{i+1}. {formula}  (Tc = {tc} K)")
        lines.append(f"   priority score: {row['priority']:.3f}")
        lines.append(f"   note: {caveat}")
        lines.append("")

    return "\n".join(lines)