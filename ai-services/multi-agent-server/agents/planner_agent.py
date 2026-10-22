import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

# Allows `python agents/planner_agent.py` as well as `from agents.planner_agent import ...`
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.feature_sources import FEATURES, describe_source


BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "planner_prompt.txt"

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

PLANNER_MAX_TOKENS = int(
    os.getenv(
        "PLANNER_MAX_TOKENS",
        "120" if FAST_MODE else "300"
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


def default_steps() -> List[Dict[str, Any]]:
    return [
        {
            "step": 1,
            "agent": "planner_agent",
            "action": "Create workflow plan"
        },
        {
            "step": 2,
            "agent": "worker_agent",
            "action": "Retrieve database evidence and generate output"
        },
        {
            "step": 3,
            "agent": "reviewer_agent",
            "action": "Review output for risk, correction, retest, and recommendation"
        },
        {
            "step": 4,
            "agent": "human_reviewer",
            "action": "Accept, partially accept, or reject"
        }
    ]


def describe_context(
    feature: Optional[str]
) -> str:
    if feature not in FEATURES:
        return "Feature: not specified\nEvidence Source: not specified"

    return (
        f"Feature: {FEATURES[feature]['label']} ({feature})\n"
        f"Evidence Source: {describe_source(feature)}"
    )


def call_model(
    user_request: str,
    feature: Optional[str] = None
) -> tuple[str, Optional[str]]:
    prompt = f"""
{load_prompt()}

Constraints:
- Keep output concise.
- Provide exactly 3 milestones.
- Keep response under 140 words.

Context:

{describe_context(feature)}

User Request:

{user_request}
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
            max_tokens=PLANNER_MAX_TOKENS
        )

        return response.choices[0].message.content.strip(), None

    except Exception as exc:
        return (
            "Objective: Process the user request.\n"
            "Steps: Plan, work, review, human decision.\n"
            "Evidence Required: Records from the feature's database API.\n"
            "Human Approval: Required.\n"
            f"Fallback Reason: {exc}"
        ), str(exc)


def plan_workflow(
    user_request: str,
    feature: Optional[str] = None
) -> Dict[str, Any]:
    plan, model_error = call_model(
        user_request,
        feature
    )

    result = {
        "status": "fallback" if model_error else "success",
        "agent": "planner_agent",
        "model": OLLAMA_MODEL,
        "objective": user_request,
        "feature": feature,
        "plan": plan,
        "steps": default_steps(),
        "human_approval_required": True
    }
    if model_error:
        result["error"] = model_error

    return result


if __name__ == "__main__":
    import json

    result = plan_workflow(
        "Generate a card status summary for user_id(1).",
        "cards"
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )