"""Hydride candidate triage — formal entry point.

Ranks the published hydride superconductors under a chosen decision policy and
prints a data-grounded validation plan for the top candidates.

Usage:
    python3 run_triage.py --policy max_tc
    python3 run_triage.py --policy lab_feasible_first
    python3 run_triage.py --policy balanced --top 5
"""

import argparse

from triage.hydrides import load_hydrides, rank_by_policy, make_validation_plan, POLICIES


def main():
    # Set up command-line arguments.
    parser = argparse.ArgumentParser(description="Hydride candidate triage")
    parser.add_argument(
        "--policy",
        default="balanced",
        choices=list(POLICIES.keys()),       # only allow defined policy names
        help="which decision policy to rank by",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="how many top candidates to show",
    )
    args = parser.parse_args()

    # Load data and run the triage.
    df = load_hydrides()

    # Show the ranked table.
    ranked = rank_by_policy(df, args.policy)
    print(f"\n=== Ranking under policy: {args.policy} ===")
    print(ranked[["formula", "tc_allen_dynes", "priority"]].head(args.top).to_string(index=False))

    # Show the validation plan.
    print()
    print(make_validation_plan(df, args.policy, top_n=args.top))


if __name__ == "__main__":
    main()