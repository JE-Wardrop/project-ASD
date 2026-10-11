import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BASE_DIR.parent
PROMPT_PATH = BASE_DIR / "prompts" / "worker_prompt.txt"
DATABASE_PATH = APP_DIR / "enrolment.db"

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

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=OLLAMA_TIMEOUT_SECONDS
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    ).strip()


def extract_subject_code(
    user_request: str
) -> str:
    request_upper = user_request.upper()

    for token in request_upper.replace(".", " ").replace(",", " ").split():
        if token.startswith("ASD"):
            return token

    return "ASD101"


def _connect_db() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def get_students_by_subject(
    subject_code: str
) -> List[Dict[str, Any]]:
    conn = _connect_db()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT student_id, student_name, subject_code
            FROM students
            WHERE subject_code = ?
            ORDER BY student_id
            """,
            (subject_code,),
        )

        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def format_evidence(
    students: List[Dict[str, Any]],
    subject_code: str
) -> str:
    if not students:
        return f"No students found for {subject_code}."

    lines = []

    for student in students:
        lines.append(
            f"- {student['student_id']} | "
            f"{student['student_name']} | "
            f"{student['subject_code']}"
        )

    return "\n".join(lines)


def call_model(
    user_request: str,
    subject_code: str,
    evidence_text: str
) -> str:
    prompt = f"""
{load_prompt()}

Constraints:
- Use only the provided Student Evidence.
- Do not invent students or fields.
- Return concise output under 180 words.

User Request:

{user_request}

Subject Code:

{subject_code}

Student Evidence:

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

        return response.choices[0].message.content.strip()

    except Exception as exc:
        return (
            "Output:\n"
            "Model output could not be generated.\n\n"
            "Evidence Used:\n"
            f"{evidence_text}\n\n"
            "Limitations:\n"
            f"Model call failed. Human review required. Error: {exc}"
        )


def generate_output(
    user_request: str
) -> Dict[str, Any]:
    subject_code = extract_subject_code(
        user_request
    )

    try:
        students = get_students_by_subject(
            subject_code
        )

        evidence_text = format_evidence(
            students,
            subject_code
        )

        output = call_model(
            user_request,
            subject_code,
            evidence_text
        )

        return {
            "status": "success",
            "agent": "worker_agent",
            "model": OLLAMA_MODEL,
            "subject_code": subject_code,
            "evidence_count": len(students),
            "evidence": students,
            "output": output,
            "human_approval_required": True
        }

    except (FileNotFoundError, sqlite3.Error) as exc:
        return {
            "status": "error",
            "agent": "worker_agent",
            "subject_code": subject_code,
            "evidence_count": 0,
            "evidence": [],
            "output": "Database evidence could not be retrieved.",
            "error": str(exc),
            "human_approval_required": True
        }


if __name__ == "__main__":
    import json

    result = generate_output(
        "Generate a student enrolment summary for ASD101."
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )