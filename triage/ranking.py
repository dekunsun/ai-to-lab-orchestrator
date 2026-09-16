"""Rank candidates under a decision policy, and test how stable that ranking is.

Reuses policy/WeightedPolicy — the same mechanism that sets the CdTe objective.
One trade-off machinery for both halves of the system, so "why is this ranked
first?" and "why did this experiment score 0.898?" have the same shape of answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from policy.weighted_policy import WeightedPolicy
from triage.hydride_loader import HydrideCandidate


@dataclass
class RankedCandidate:
    rank: int
    candidate: HydrideCandidate
    score: float
    contributions: dict[str, float]


def rank(candidates: list[HydrideCandidate], policy: WeightedPolicy) -> list[RankedCandidate]:
    """Score every candidate under one policy, best first.

    Ties break on formula so the ordering is deterministic — an unstable sort
    would make the sensitivity analysis below report phantom rank movement.
    """
    scored = [
        (policy.score(c.metrics), policy.contributions(c.metrics), c)
        for c in candidates
    ]
    scored.sort(key=lambda t: (-t[0], t[2].formula))
    return [RankedCandidate(i, c, round(s, 4), {k: round(v, 4) for k, v in contrib.items()})
            for i, (s, contrib, c) in enumerate(scored, start=1)]


def sensitivity(candidates: list[HydrideCandidate],
                policies: list[WeightedPolicy]) -> list[dict[str, Any]]:
    """Compare ranks across policies and report how much each candidate moves.

    This is the output that matters more than any single ranking. A candidate
    that sits near the top under every policy is robust to the disagreement
    between them; one that swings by ten places is only there because of a
    weighting someone chose, and saying so is the honest way to present it.
    """
    per_policy = {p.policy_id: {rc.candidate.candidate_id: rc for rc in rank(candidates, p)}
                  for p in policies}

    rows = []
    for c in candidates:
        ranks = {pid: per_policy[pid][c.candidate_id].rank for pid in per_policy}
        spread = max(ranks.values()) - min(ranks.values())
        rows.append({
            "candidate_id": c.candidate_id,
            "formula": c.formula,
            "ranks": ranks,
            "best_rank": min(ranks.values()),
            "rank_spread": spread,
            "stability": "stable" if spread <= 2 else
                         "moderate" if spread <= 6 else "policy-driven",
        })
    rows.sort(key=lambda r: (r["best_rank"], r["rank_spread"]))
    return rows


def consensus_shortlist(sens: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    """Candidates that land in the top N under EVERY policy considered.

    The useful question for a program lead is not "what is rank 1" but "what
    would we validate regardless of whose priorities win the argument". That
    set is where experimental time is least likely to be wasted on a weighting
    dispute.
    """
    return [r for r in sens if all(v <= top_n for v in r["ranks"].values())]
