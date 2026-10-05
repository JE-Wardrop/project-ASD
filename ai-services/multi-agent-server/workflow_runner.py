import json

from coordinator import run_workflow


def main() -> None:
    result = run_workflow(
        # "Generate a summary for" + student
        "Generate a summary for each microservice."
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )


if __name__ == "__main__":
    main()