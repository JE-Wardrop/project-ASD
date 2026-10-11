import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI

# Allows `python agents/worker_agent.py` as well as `from agents.worker_agent import ...`
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.feature_sources import (
    FEATURES,
    EvidenceError,
    describe_source,
    fetch_evidence,
    resolve_feature,
)


BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "worker_prompt.txt"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b"
)

OLLAMA_TIMEOUT_SECONDS = float(
    os.getenv("OLLAMA_TIMEOUT_SECONDS", "45")
)

FAST_MODE = os.getenv(
    "FAST_MODE",
    "true"
).lower() == "true"

WORKER_MAX_TOKENS = int(
    os.getenv(
        "WORKER_MAX_TOKENS",
        "180" if FAST_MODE else "400"
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


def format_evidence(
    evidence: Dict[str, Any]
) -> str:
    records = evidence["records"]
    if not records:
        return f"No records found in {evidence['source']} for the requested filters."

    lines = [
        f"Source: {evidence['source']}",
        f"Records shown: {len(records)} of {evidence['matched_records']} matching "
        f"({evidence['total_records']} total)",
    ]
    if evidence["filters_applied"]:
        lines.append(f"Filters applied: {evidence['filters_applied']}")

    for record in records:
        lines.append(f"- {json.dumps(record)}")

    return "\n".join(lines)


def call_model(
    user_request: str,
    feature: str,
    evidence_text: str
) -> tuple[str, Optional[str]]:
    prompt = f"""
{load_prompt()}

Constraints:
- Use only the provided Feature Evidence.
- Do not invent records or fields.
- Return concise output under 180 words.

User Request:

{user_request}

Feature:

{FEATURES[feature]['label']} ({feature})

Feature Evidence:

{evidence_text}
"""

    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=WORKER_MAX_TOKENS
        )

        return response.choices[0].message.content.strip(), None

    except Exception as exc:
        return (
            "Output:\n"
            "Model output could not be generated.\n\n"
            "Evidence Used:\n"
            f"{evidence_text}\n\n"
            "Limitations:\n"
            f"Model call failed. Human review required. Error: {exc}"
        ), str(exc)


def generate_output(
    user_request: str,
    feature: Optional[str] = None
) -> Dict[str, Any]:
    try:
        feature = resolve_feature(
            feature,
            None,
            user_request
        )
    except ValueError as exc:
        return {
            "status": "error",
            "agent": "worker_agent",
            "feature": feature,
            "evidence_count": 0,
            "evidence": [],
            "output": "No feature evidence source could be selected.",
            "error": str(exc),
            "human_approval_required": True
        }

    try:
        evidence = fetch_evidence(
            feature,
            user_request
        )
    except EvidenceError as exc:
        return {
            "status": "error",
            "agent": "worker_agent",
            "feature": feature,
            "evidence_source": describe_source(feature),
            "evidence_count": 0,
            "evidence": [],
            "output": "Database evidence could not be retrieved.",
            "error": str(exc),
            "human_approval_required": True
        }

    output, model_error = call_model(
        user_request,
        feature,
        format_evidence(evidence)
    )

    result = {
        "status": "fallback" if model_error else "success",
        "agent": "worker_agent",
        "model": OLLAMA_MODEL,
        "feature": feature,
        "evidence_source": evidence["source"],
        "evidence_count": len(evidence["records"]),
        "matched_records": evidence["matched_records"],
        "total_records": evidence["total_records"],
        "filters_applied": evidence["filters_applied"],
        "filters_ignored": evidence["filters_ignored"],
        "evidence": evidence["records"],
        "output": output,
        "human_approval_required": True
    }
    if model_error:
        result["error"] = model_error

    return result


if __name__ == "__main__":
    result = generate_output(
        "Generate a card status summary for user_id(1).",
        "cards"
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
