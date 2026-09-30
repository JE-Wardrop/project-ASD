import os
from pathlib import Path

import requests


REQUIRED_RAG_TOOLS = [
    "refresh_corpus",
    "retrieve_context",
    "answer_question"
]

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:5003")

# Which RAG feature filter (rag_pipeline.DB_SOURCES) belongs to each review
# target, and one in-scope question to ask it. The out-of-scope question must
# come back as insufficient context (the grounded-answer contract).
TARGET_FEATURES = {
    "student-1": ("cards", "How many cards are there?"),
    "student-2": ("accounts", "How many accounts are there?"),
    "student-4": ("users", "How many users are there?"),
    "student-5": ("transactions", "How many transactions are there?"),
}
OUT_OF_SCOPE_QUESTION = "What is the weather in Sydney today?"


def _answer(query: str, feature: str | None, caller: str) -> dict:
    resp = requests.post(
        f"{RAG_SERVICE_URL}/answer",
        json={"query": query, "k": 5, "caller": caller, "feature": feature},
        timeout=180,
    )
    return resp.json()


def _live_check(target) -> tuple[bool, str]:
    """ACT against the running RAG server, the same way the feature backend does."""
    if target.key not in TARGET_FEATURES:
        return True, f"no RAG feature mapped for {target.key}, live check skipped"

    feature, question = TARGET_FEATURES[target.key]
    caller = f"agentic-loop-{target.key}"
    try:
        grounded = _answer(question, feature, caller)
        off_topic = _answer(OUT_OF_SCOPE_QUESTION, feature, caller)
    except requests.RequestException as exc:
        return False, f"RAG server not reachable at {RAG_SERVICE_URL}: {exc}"
    except ValueError:
        return False, f"RAG server at {RAG_SERVICE_URL} returned a non-JSON reply"

    if grounded.get("status") != "success":
        return False, f"answer_question failed for feature={feature}: {grounded.get('error')}"

    citations = grounded.get("citations", [])
    confidence = grounded.get("confidence_category")
    if not citations or confidence in (None, "Insufficient", "Unknown"):
        return False, (
            f"'{question}' (feature={feature}) was not grounded: "
            f"confidence={confidence}, citations={len(citations)}"
        )

    if off_topic.get("confidence_category") != "Insufficient" or off_topic.get("citations"):
        return False, (
            f"out-of-scope question was answered instead of returning insufficient context "
            f"(confidence={off_topic.get('confidence_category')})"
        )

    return True, (
        f"live answer_question for feature={feature}: '{question}' -> "
        f"'{grounded.get('answer', '').strip()[:80]}', confidence={confidence}, "
        f"{len(citations)} citation(s), top_chunk={grounded['retrieval_summary']['top_chunk']}; "
        f"out-of-scope question -> confidence=Insufficient with 0 citations"
    )


def collect(target, repo_root: Path) -> tuple[bool, str]:
    rag_server_dir = repo_root / "ai-services/rag-server"

    required_paths = [
        rag_server_dir / "rag_pipeline.py",
        rag_server_dir / "rag_server.py",
        rag_server_dir / "requirements.txt",
    ]

    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "RAG evidence incomplete. Missing: " + ", ".join(missing)

    pipeline_text = (rag_server_dir / "rag_pipeline.py").read_text(encoding="utf-8")

    missing_tools = [tool for tool in REQUIRED_RAG_TOOLS if f"def {tool}" not in pipeline_text]
    if missing_tools:
        return False, "rag_pipeline.py missing required tools: " + ", ".join(missing_tools)

    live_ok, live_evidence = _live_check(target)
    if not live_ok:
        return False, f"RAG live validation failed: {live_evidence}"

    return True, (
        "RAG evidence: rag-server/ contains rag_pipeline.py and rag_server.py; "
        f"{len(REQUIRED_RAG_TOOLS)} tools defined (refresh_corpus, retrieve_context, answer_question); "
        f"{live_evidence}."
    )
