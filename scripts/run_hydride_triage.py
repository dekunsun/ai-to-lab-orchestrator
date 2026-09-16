"""Hydride candidate triage: published data -> ranking -> sensitivity -> validation plan.

    python scripts/run_hydride_triage.py
    python scripts/run_hydride_triage.py --policy configs/policies/hydride_lab_feasible_first.yaml

Produces the ranked shortlist, a cross-policy sensitivity table, a generated
validation workflow for the top candidate, and a registered hypothesis.

No physics is simulated anywhere in this pipeline. Every number traces back to
either the published table in datasets/hydrides/ or a documented rule in
triage/derive.py — see datasets/hydrides/SOURCE.md.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import store
from orchestrator import safety_gate
from orchestrator.workflow_parser import load_workflow
from policy.weighted_policy import WeightedPolicy
from triage.hydride_loader import DATASET, load
from triage.ranking import consensus_shortlist, rank, sensitivity
from triage.validation_plan import hypothesis_for, write_plan

DEFAULT_POLICY = "configs/policies/hydride_balanced_validation.yaml"
OUT_DIR = "artifacts/triage_results"


def all_policies() -> list[WeightedPolicy]:
    return [WeightedPolicy.from_yaml(p)
            for p in sorted(glob.glob("configs/policies/hydride_*.yaml"))]


def print_ranking(ranked, policy, top_n) -> None:
    print(f"\n── Ranked under: {policy.name} ({policy.policy_id}) "
          f"─ top {top_n} of {len(ranked)}\n")
    print(f"{'#':>2}  {'formula':<11} {'score':>6}  {'Tc(K)':>6} {'method':<12} "
          f"{'λ':>5} {'conf':>5} {'feas':>5}  limiting element")
    print("─" * 92)
    for rc in ranked[:top_n]:
        c, d = rc.candidate, rc.candidate.derivation
        print(f"{rc.rank:>2}  {c.formula:<11} {rc.score:>6.3f}  "
              f"{c.best_tc_k:>6.1f} {d['tc']['method']:<12} "
              f"{c.lambda_ep:>5.2f} {c.metrics['tc_confidence']:>5.2f} "
              f"{c.metrics['synthesis_feasibility']:>5.2f}  "
              f"{d['feasibility']['limiting_element']}")


def print_sensitivity(sens, policies, top_n) -> None:
    print(f"\n── Ranking sensitivity across {len(policies)} policies "
          f"─ top {top_n}\n")
    short = {"hydride_balanced_validation": "balanced",
             "hydride_high_tc_seeking": "high-Tc",
             "hydride_lab_feasible_first": "feasible"}
    heads = [short.get(p.policy_id, p.policy_id[:9]) for p in policies]
    print(f"{'formula':<11} " + " ".join(f"{h:>9}" for h in heads) +
          f" {'spread':>7}  stability")
    print("─" * 66)
    for r in sens[:top_n]:
        cells = " ".join(f"{r['ranks'][p.policy_id]:>9}" for p in policies)
        print(f"{r['formula']:<11} {cells} {r['rank_spread']:>7}  {r['stability']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=DEFAULT_POLICY)
    ap.add_argument("--dataset", default=DATASET)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--no-persist", action="store_true")
    args = ap.parse_args()

    candidates = load(args.dataset)
    policy = WeightedPolicy.from_yaml(args.policy)
    policies = all_policies()

    n_refined = sum(1 for c in candidates if c.has_refined_tc)
    print(f"\nHydride candidate triage")
    print(f"  {len(candidates)} published candidates from {args.dataset}")
    print(f"  {n_refined} of {len(candidates)} have a beyond-Allen-Dynes Tc; "
          f"the rest are Allen-Dynes only")

    ranked = rank(candidates, policy)
    print_ranking(ranked, policy, args.top)

    sens = sensitivity(candidates, policies)
    print_sensitivity(sens, policies, args.top)

    consensus = consensus_shortlist(sens, top_n=5)
    print(f"\n── Consensus shortlist ─ top 5 under every policy\n")
    if consensus:
        for r in consensus:
            print(f"   {r['formula']:<11} ranks {r['ranks']}")
        print("\n   These are worth validating regardless of whose priorities win.")
    else:
        print("   None. Every candidate's standing depends on the weighting chosen,\n"
              "   which is itself the finding: this cohort has no policy-independent pick.")

    # --- the join into the execution half of the system ---
    top = ranked[0]
    plan_path = write_plan(top, policy.policy_id)
    wf = load_workflow(plan_path)                       # same parser as CdTe
    probe = {"anneal_temp_c": 750.0, "anneal_time_h": 24.0, "h2_pressure_bar": 150.0}
    verdict = safety_gate.review_parameters(wf, probe)  # same gate as CdTe

    print(f"\n── Validation plan for {top.candidate.formula}\n")
    print(f"   workflow      {plan_path}")
    print(f"   parsed by     orchestrator.workflow_parser (unchanged)")
    print(f"   gate check    {probe} -> {verdict['approval_status']}"
          + (f" [{verdict['blocked_by']}]" if verdict["blocked_by"] else ""))
    print(f"   execution     {wf.raw['execution_status']['state']}")

    hyp = hypothesis_for(top, policy.policy_id)
    print(f"\n── Hypothesis {hyp['hypothesis_id']}\n")
    print(f"   claim      {hyp['claim']}")
    print(f"   settles    {hyp['what_this_settles']}")
    for caveat in hyp["known_caveats"]:
        print(f"   caveat     {caveat}")

    if not args.no_persist:
        conn = store.connect()
        store.save_hypothesis(conn, hyp, source=args.dataset)
        conn.close()
        print(f"\n   registered in db/lab.sqlite (hypotheses)")

    os.makedirs(args.out, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": args.dataset,
        "policy": policy.provenance(),
        "n_candidates": len(candidates),
        "n_with_refined_tc": n_refined,
        "ranking": [
            {"rank": rc.rank, "candidate_id": rc.candidate.candidate_id,
             "formula": rc.candidate.formula, "score": rc.score,
             "contributions": rc.contributions,
             "metrics": rc.candidate.metrics,
             "derivation": rc.candidate.derivation}
            for rc in ranked],
        "sensitivity": sens,
        "consensus_shortlist": [r["formula"] for r in consensus],
        "validation_plan": plan_path,
        "hypothesis": hyp,
    }
    out_path = os.path.join(args.out, "hydride_triage.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"   wrote {out_path}\n")


if __name__ == "__main__":
    main()
