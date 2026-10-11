import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "reviewer_prompt.txt"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1"
)

OLLAMA_REVIEW_MODEL = os.getenv(
    "OLLAMA_REVIEW_MODEL",
    "llama3.1:8b"
)

# Used when the review model cannot run (e.g. llama3.1:8b out of memory),
# so the workflow still gets a review instead of a canned failure message.
OLLAMA_REVIEW_FALLBACK_MODEL = os.getenv(
    "OLLAMA_REVIEW_FALLBACK_MODEL",
    os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
)

OLLAMA_TIMEOUT_SECONDS = float(
    os.getenv("OLLAMA_TIMEOUT_SECONDS", "45")
)

FAST_MODE = os.getenv(
    "FAST_MODE",
    "true"
).lower() == "true"

REVIEWER_MAX_TOKENS = int(
    os.getenv(
        "REVIEWER_MAX_TOKENS",
        "160" if FAST_MODE else "400"
    )
)

# No silent retries: the coordinator's step timeout must cover a single call.
client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=OLLAMA_TIMEOUT_SECONDS,
    max_retries=0
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    ).strip()


def build_prompt(
    user_request: str,
    worker_result: Dict[str, Any],
    plan: Optional[str]
) -> str:
    return f"""
{load_prompt()}

Constraints:
- Keep each section brief and actionable.
- Return only: Risk, Correction, Retest, Recommendation.
- Keep response under 160 words.

User Request:

{user_request}

Planner Plan:

{plan or "No plan was supplied."}

Worker Result:

{json.dumps(worker_result, indent=2)}
"""


def call_model(
    model: str,
    prompt: str
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=REVIEWER_MAX_TOKENS
    )

    return response.choices[0].message.content.strip()


def review_output(
    user_request: str,
    worker_result: Dict[str, Any],
    plan: Optional[str] = None
) -> Dict[str, Any]:
    prompt = build_prompt(
        user_request,
        worker_result,
        plan
    )

    try:
        return {
            "status": "success",
            "agent": "reviewer_agent",
            "model": OLLAMA_REVIEW_MODEL,
            "review": call_model(OLLAMA_REVIEW_MODEL, prompt),
            "human_approval_required": True
        }
    except Exception as exc:
        review_error = str(exc)

    if OLLAMA_REVIEW_FALLBACK_MODEL and OLLAMA_REVIEW_FALLBACK_MODEL != OLLAMA_REVIEW_MODEL:
        try:
            return {
                "status": "success",
                "agent": "reviewer_agent",
                "model": OLLAMA_REVIEW_FALLBACK_MODEL,
                "fallback_from": OLLAMA_REVIEW_MODEL,
                "fallback_reason": review_error,
                "review": call_model(OLLAMA_REVIEW_FALLBACK_MODEL, prompt),
                "human_approval_required": True
            }
        except Exception as exc:
            review_error = f"{review_error}; fallback {OLLAMA_REVIEW_FALLBACK_MODEL}: {exc}"

    return {
        "status": "fallback",
        "agent": "reviewer_agent",
        "model": OLLAMA_REVIEW_MODEL,
        "review": (
            "Risk: Review model unavailable.\n"
            "Correction: Verify Ollama and reviewer model.\n"
            "Retest: Run the workflow again.\n"
            "Recommendation: Do not approve until reviewed."
        ),
        "error": review_error,
        "human_approval_required": True
    }


if __name__ == "__main__":
    sample_worker_result = {
        "status": "success",
        "feature": "cards",
        "evidence_count": 2,
        "evidence": [
            {"card_id": 1, "user_id": 1, "status": "Frozen"},
            {"card_id": 2, "user_id": 1, "status": "Unfrozen"}
        ],
        "output": "User 1 has 2 cards: 1 frozen and 1 unfrozen."
    }

    result = review_output(
        "Generate a card status summary for user_id(1).",
        sample_worker_result,
        "Objective: Summarise card statuses for user 1."
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
