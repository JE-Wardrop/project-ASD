import json

from coordinator import run_workflow


def main() -> None:
    result = run_workflow(
        "Generate a card status summary for user_id(1).",
        "Recommend a user delete or update card details"
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )


if __name__ == "__main__":
    main()