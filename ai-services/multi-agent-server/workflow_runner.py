"""Run the Planner -> Worker -> Reviewer -> Human Review workflow from a terminal.

    python workflow_runner.py "Summarise account statuses for user_id(1)." --feature accounts
    python workflow_runner.py "..." --feature cards --decision Accept --reason "Matches evidence"
    python workflow_runner.py "..." --feature cards --no-decision

Without --decision, the human is asked for a decision when the terminal is interactive.
"""

import argparse
import json
import sys

from coordinator import (
    HUMAN_DECISIONS,
    DecisionAlreadyRecorded,
    WorkflowNotFound,
    record_decision,
    run_workflow,
)


DEFAULT_REQUEST = "Generate a card status summary for user_id(1)."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("user_request", nargs="?", default=DEFAULT_REQUEST)
    parser.add_argument("--feature", help="cards, accounts, users or transactions (inferred if omitted)")
    parser.add_argument("--caller", default="terminal")
    parser.add_argument("--decision", help=" / ".join(HUMAN_DECISIONS))
    parser.add_argument("--reason", default="")
    parser.add_argument("--correction", default="")
    parser.add_argument("--reviewer", default="terminal")
    parser.add_argument("--no-decision", action="store_true", help="leave the decision pending")
    return parser.parse_args()


def ask_for_decision() -> tuple[str, str, str] | None:
    print()
    print("HUMAN REVIEW")
    for number, value in enumerate(HUMAN_DECISIONS, start=1):
        print(f"{number} - {value}")
    print("0 - Leave pending")

    choice = input("Decision: ").strip()
    if choice not in {"1", "2", "3"}:
        return None

    decision = HUMAN_DECISIONS[int(choice) - 1]
    reason = input("Reason: ").strip()
    correction = input("Correction (required for Partially Accept): ").strip()
    return decision, reason, correction


def main() -> int:
    args = parse_args()

    try:
        result = run_workflow(
            args.user_request,
            args.feature,
            args.caller
        )
    except ValueError as exc:
        print(f"Workflow not started: {exc}")
        return 2

    print(
        json.dumps(
            result,
            indent=2
        )
    )

    if args.no_decision:
        return 0

    if args.decision:
        answer = (args.decision, args.reason, args.correction)
    elif sys.stdin.isatty():
        answer = ask_for_decision()
    else:
        answer = None

    if answer is None:
        print(f"Human decision pending for {result['workflow_id']}")
        return 0

    try:
        record = record_decision(
            result["workflow_id"],
            *answer,
            reviewer=args.reviewer
        )
    except (ValueError, WorkflowNotFound, DecisionAlreadyRecorded) as exc:
        print(f"Decision not recorded: {exc}")
        return 2

    print(
        json.dumps(
            {"human_decision": record},
            indent=2
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())