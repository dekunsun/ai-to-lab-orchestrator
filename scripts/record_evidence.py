"""Close the loop: record measurements, settle hypotheses, re-rank the cohort.

    python scripts/record_evidence.py --evidence datasets/hydrides/evidence_example.csv

Shows the ranking before and after the evidence lands, so the consequence of a
measurement is visible rather than asserted.

Evidence enters from outside the system — an instrument, a collaborator, a
paper. Nothing here simulates a measurement. The shipped example file is
explicitly marked `hypothetical_example` and the script says so loudly, because
nobody has measured these compounds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import store
from policy.weighted_policy import WeightedPolicy
from triage.evidence import assess, calibrate, load_evidence
from triage.hydride_loader import load, load_candidates, derive_metrics
from triage.ranking import rank

DEFAULT_POLICY = "configs/policies/hydride_balanced_validation.yaml"
VERDICT_MARK = {"supported": "+", "contradicted": "!", "inconclusive": "?"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default="datasets/hydrides/evidence_example.csv")
    ap.add_argument("--policy", default=DEFAULT_POLICY)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--out", default="artifacts/evidence_results")
    ap.add_argument("--no-persist", action="store_true")
    args = ap.parse_args()

    policy = WeightedPolicy.from_yaml(args.policy)
    evidence = load_evidence(args.evidence)

    before = rank(load(), policy)
    before_rank = {rc.candidate.candidate_id: rc.rank for rc in before}
    before_score = {rc.candidate.candidate_id: rc.score for rc in before}
    predicted = {rc.candidate.candidate_id: rc.candidate.best_tc_k for rc in before}

    hypothetical = [e for e in evidence if e.is_hypothetical]
    print(f"\nEvidence loop  |  {len(evidence)} record(s) from {args.evidence}")
    if hypothetical:
        print(f"\n  !! {len(hypothetical)} of {len(evidence)} records are marked "
              f"hypothetical_example.\n     Nobody has measured these compounds. They "
              f"exist to exercise the loop, not to\n     make a claim about the "
              f"materials. Never quote a number below as a result.")

    # ---- what each record settles -------------------------------------------
    print("\n── What each record settles\n")
    scored: list[tuple] = []
    for ev in evidence:
        p = predicted.get(ev.candidate_id)
        if p is None:
            print(f"  {ev.evidence_id}  candidate {ev.candidate_id} is not in "
                  f"the cohort — skipped")
            continue
        a = assess(ev, p)
        scored.append((ev, a, p))
        obs = f"{ev.observed_tc_k:g} K" if ev.observed_tc_k is not None else "no transition"
        print(f"  [{VERDICT_MARK[a['status']]}] {ev.formula:<11} {obs:<15} "
              f"floor {ev.measurement_floor_k:g} K   predicted {p:g} K   "
              f"→ {a['status'].upper()}")
        print(f"      {a['reason']}")
        print(f"      recorded by {ev.recorded_by} · {ev.method} · {ev.source_type}\n")
    assessments = [a for _, a, _ in scored]

    # ---- what it implies about the method ------------------------------------
    cal = calibrate(assessments)
    print("── What it implies about the method\n")
    print(f"  {cal.describe()}\n")
    if cal.inconclusive:
        print(f"  {cal.inconclusive} inconclusive record(s) excluded from the "
              f"calibration. An experiment that\n  could not have seen the effect is "
              f"not evidence the effect is absent.\n")

    # ---- re-rank -------------------------------------------------------------
    after = rank(derive_metrics(load_candidates(), evidence=evidence), policy)
    print("── Cohort after the evidence lands\n")
    print(f"{'#':>2}  {'formula':<11} {'was':>4} {'move':>6}  {'score':>6} {'Δ':>7}  "
          f"{'Tc (K)':>7} {'source':<12} conf")
    print("─" * 78)
    for rc in after[:args.top]:
        cid = rc.candidate.candidate_id
        was = before_rank[cid]
        delta_rank = was - rc.rank
        move = "—" if delta_rank == 0 else f"{delta_rank:+d}"
        dscore = rc.score - before_score[cid]
        d = rc.candidate.derivation
        print(f"{rc.rank:>2}  {rc.candidate.formula:<11} {was:>4} {move:>6}  "
              f"{rc.score:>6.3f} {dscore:>+8.3f}  {rc.candidate.best_tc_k:>7.1f} "
              f"{d['tc']['method']:<12} {rc.candidate.metrics['tc_confidence']:.2f}")

    movers = [(before_rank[rc.candidate.candidate_id] - rc.rank, rc) for rc in after]
    movers.sort(key=lambda t: -abs(t[0]))
    big = [m for m in movers if abs(m[0]) >= 2][:3]
    if big:
        print("\n  Largest moves: " + ", ".join(
            f"{rc.candidate.formula} {d:+d}" for d, rc in big))
    print("\n  Note the second-order effect: measuring the leader low also moved "
          "candidates\n  nobody tested. Tc is normalized against the best in the "
          "cohort, so when the\n  leader falls, every untested compound becomes "
          "relatively more attractive \u2014 partly\n  offset by the confidence "
          "penalty the same evidence applied to the method.")

    # ---- persist -------------------------------------------------------------
    if not args.no_persist:
        conn = store.connect()
        settled = 0
        for ev, a, p in scored:
            hyp_id = f"HYP-{ev.candidate_id}"
            store.save_evidence(conn, ev, a, p, hyp_id)
            if a["status"] != "inconclusive":
                if store.update_hypothesis_status(conn, hyp_id, a["status"], a["reason"]):
                    settled += 1
        conn.close()
        print(f"\n  {len(scored)} record(s) written to db/lab.sqlite · "
              f"{settled} hypothesis(es) settled")
        print("  Inconclusive results leave their hypothesis open — an experiment was "
              "spent\n  without answering the question, and the registry keeps that fact.")

    artifact = _write_artifact(args.out, args.evidence, policy, scored, cal,
                               before, after, before_rank, before_score)
    print(f"\n  wrote {artifact}\n")


def _write_artifact(out_dir, evidence_path, policy, scored, cal, before, after,
                    before_rank, before_score):
    """Persist the whole before/after picture so downstream readers - the
    dashboard, the deck - never have to re-derive or hand-copy these numbers."""
    os.makedirs(out_dir, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence_file": evidence_path,
        "policy": policy.provenance(),
        "all_hypothetical": all(ev.is_hypothetical for ev, _, _ in scored),
        "records": [
            {"evidence_id": ev.evidence_id, "formula": ev.formula,
             "observed_tc_k": ev.observed_tc_k,
             "measurement_floor_k": ev.measurement_floor_k,
             "predicted_tc_k": p, "method": ev.method,
             "source_type": ev.source_type, "recorded_by": ev.recorded_by,
             "verdict": a["status"], "direction": a.get("direction"),
             "reason": a["reason"]}
            for ev, a, p in scored],
        "calibration": {
            "method": cal.method, "n_conclusive": cal.n,
            "n_inconclusive": cal.inconclusive,
            "factor": cal.factor, "penalty": cal.penalty,
            "description": cal.describe()},
        "ranking_after": [
            {"rank": rc.rank, "was": before_rank[rc.candidate.candidate_id],
             "move": before_rank[rc.candidate.candidate_id] - rc.rank,
             "formula": rc.candidate.formula, "score": rc.score,
             "score_delta": round(rc.score - before_score[rc.candidate.candidate_id], 4),
             "tc_k": rc.candidate.best_tc_k,
             "tc_source": rc.candidate.derivation["tc"]["method"],
             "confidence": rc.candidate.metrics["tc_confidence"]}
            for rc in after],
    }
    path = os.path.join(out_dir, "evidence_loop.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


if __name__ == "__main__":
    main()
