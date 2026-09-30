"""Retrieval evaluation (P@5 and R@5) — same structure as Lab 8.

Run after the database containers are up and the corpus has been refreshed:
    python rag_eval.py
Writes retrieval-metrics.md for the technical report.

Every place that differs from Lab 8 is marked with  # CHANGED FROM LAB 8
"""

from pathlib import Path

from rag_pipeline import retrieve_context

METRICS_PATH = Path(__file__).resolve().parent / "retrieval-metrics.md"

# CHANGED FROM LAB 8: benchmark questions for this project instead of the
# student-enrolment questions. The last one is unrelated on purpose: it
# should retrieve nothing (insufficient-context check).
BENCHMARKS = [
    {
        "query": "failed transactions",
        "feature": "transactions",
        "relevant_keywords": ["status=FAILED"],
        "expected_relevant": 1,
    },
    {
        "query": "how many transactions are there",
        "feature": "transactions",
        "relevant_keywords": ["count is"],
        "expected_relevant": 1,
    },
    {
        "query": "can a completed transaction be cancelled",
        "feature": "transactions",
        "relevant_keywords": ["cannot be cancelled"],
        "expected_relevant": 1,
    },
    {
        "query": "frozen cards",
        "feature": "cards",
        "relevant_keywords": ["status=FROZEN"],
        "expected_relevant": 1,
    },
    {
        "query": "frozen accounts",
        "feature": "accounts",
        "relevant_keywords": ["account_status=FROZEN", "FROZEN account"],
        "expected_relevant": 2,
    },
    {
        "query": "can a frozen account receive a deposit",
        "feature": "accounts",
        "relevant_keywords": ["cannot receive a deposit"],
        "expected_relevant": 1,
    },
    {
        "query": "how many accounts are there",
        "feature": "accounts",
        "relevant_keywords": ["count is"],
        "expected_relevant": 1,
    },
    {
        "query": "weather in Sydney",
        "feature": None,
        "relevant_keywords": [],
        "expected_relevant": 0,
    },
]


def is_relevant(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def evaluate_query(benchmark: dict) -> dict:
    response = retrieve_context(benchmark["query"], 5, caller="rag_eval", feature=benchmark["feature"])
    results = response.get("results", [])[:5]

    relevant = [r for r in results if is_relevant(r.get("text", ""), benchmark["relevant_keywords"])]

    # CHANGED FROM LAB 8: Lab 8 always divided by 5 because it always
    # returned 5 chunks. Irrelevant chunks are now filtered out, so precision
    # is divided by what was actually retrieved.
    retrieved_count = len(results)
    precision_at_5 = len(relevant) / retrieved_count if retrieved_count else 0.0

    if benchmark["expected_relevant"] == 0:
        # Unrelated question: full marks when nothing was retrieved.
        recall_at_5 = 1.0 if retrieved_count == 0 else 0.0
        precision_at_5 = recall_at_5
    else:
        recall_at_5 = min(1.0, len(relevant) / benchmark["expected_relevant"])

    return {
        "query": benchmark["query"],
        "feature": benchmark["feature"] or "all",
        "retrieved_chunk_ids": [r.get("chunk_id") for r in results],
        "relevant_chunk_ids": [r.get("chunk_id") for r in relevant],
        "p_at_5": round(precision_at_5, 2),
        "r_at_5": round(recall_at_5, 2),
    }


def write_metrics_report(results: list[dict]) -> None:
    lines = ["# Retrieval Metrics", ""]
    for result in results:
        lines.append(f"## {result['query']} (feature: {result['feature']})")
        lines.append(f"- Retrieved: {result['retrieved_chunk_ids']}")
        lines.append(f"- Relevant: {result['relevant_chunk_ids']}")
        lines.append(f"- P@5: {result['p_at_5']}")
        lines.append(f"- R@5: {result['r_at_5']}")
        lines.append("")
    METRICS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    results = []
    for benchmark in BENCHMARKS:
        result = evaluate_query(benchmark)
        results.append(result)
        print(f"{result['query']:<45} P@5={result['p_at_5']}  R@5={result['r_at_5']}")
    write_metrics_report(results)
    print(f"\nWrote {METRICS_PATH.name}")


if __name__ == "__main__":
    main()