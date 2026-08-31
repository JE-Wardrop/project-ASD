import os
import sqlite3
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

# ============================= Agents Env Setup =============================
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

PROMPT_DIR = Path(__file__).with_name("prompts")

# Adjust if your DB lives elsewhere (matches app.py's DATABASE_NAME path)
DATABASE_NAME = Path(__file__).parent.parent / "database" / "users.db"

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1"
)

IMPLEMENTATION_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b"
)

REVIEW_MODEL = os.getenv(
    "OLLAMA_REVIEW_MODEL",
    "llama3.1:8b"
)

# ==================================== Plan ====================================
PLAN = {
    "goal": "Validate User Management App behavior using a local multi-agent workflow",
    "db_plan": [
        "Check user data quality (required fields present, no malformed rows)",
        "Check username/email uniqueness holds across all rows"
    ],
    "endpoints_plan": [
        "GET /users - get all users",
        "GET /users/<user_id> - get a single user",
        "POST /users/login - login check (connectivity/response shape only)",
        "POST /users/help - AI help endpoint"
    ]
}

# ================================ Observe: Database ================================
def validate_user(user):
    user_id, username, email, first_name, last_name, phone = user

    if not isinstance(user_id, int):
        return False, "user_id must be an integer"

    if not username:
        return False, "username is required"

    if not email or "@" not in email:
        return False, "email is required and must look like an email"

    return True, "ok"


def observe_data_quality():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    users = cursor.execute(
        """
        SELECT
            user_id,
            username,
            email,
            first_name,
            last_name,
            phone
        FROM users
        """
    ).fetchall()

    conn.close()

    if len(users) == 0:
        return False, "Expected at least one user, found none"

    all_ok = True

    for user in users:
        ok, msg = validate_user(user)
        status = "OK" if ok else f"FAIL: {msg}"
        print(f"  Checked user_id={user[0]} -> {status}")

        if not ok:
            all_ok = False

    if not all_ok:
        return False, "One or more user records failed validation"

    return True, f"Data validation passed for {len(users)} users"


def observe_uniqueness():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    rows = cursor.execute(
        "SELECT username, email FROM users"
    ).fetchall()

    conn.close()

    usernames = [r[0] for r in rows]
    emails = [r[1] for r in rows]

    dup_usernames = {u for u in usernames if usernames.count(u) > 1}
    dup_emails = {e for e in emails if emails.count(e) > 1}

    if dup_usernames:
        print(f"  Checked usernames -> FAIL: duplicates {dup_usernames}")
        return False, f"Duplicate usernames found: {dup_usernames}"

    if dup_emails:
        print(f"  Checked emails -> FAIL: duplicates {dup_emails}")
        return False, f"Duplicate emails found: {dup_emails}"

    print("  Checked usernames -> OK")
    print("  Checked emails -> OK")

    return True, "Uniqueness validation passed"


def get_sample_user():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    row = cursor.execute(
        """
        SELECT user_id, username
        FROM users
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    return row


# ============================= Observe: Live Endpoints ==============================
def observe_live_endpoints(sample_user):
    results = []

    user_id, username = (
        sample_user if sample_user else (None, None)
    )

    def check(label, method, url, **kwargs):
        try:
            response = requests.request(
                method, url, timeout=5, **kwargs
            )
            content_ok = bool(response.text and response.text.strip())
            line = (
                f"{label} -> HTTP {response.status_code}, "
                f"content_ok={content_ok}"
            )
        except Exception as exc:
            line = f"{label} -> error: {exc}"

        print(f"  Checked {line}")
        results.append(line)

    check("/users", "GET", f"{BASE_URL}/users")

    if user_id is not None:
        check(
            "/users/<user_id>",
            "GET",
            f"{BASE_URL}/users/{user_id}"
        )
    else:
        skipped = "/users/<user_id> -> skipped: no sample user found"
        print(f"  Checked {skipped}")
        results.append(skipped)

    # Deliberately wrong password: we only care that the endpoint responds
    # sanely (400/401), not that it succeeds - we don't have the plaintext.
    check(
        "/users/login",
        "POST",
        f"{BASE_URL}/users/login",
        data={
            "username": username or "nonexistent_user",
            "password": "definitely_wrong_password"
        }
    )

    check(
        "/users/help",
        "POST",
        f"{BASE_URL}/users/help",
        data={"question": "What does this app do?"}
    )

    return results


# =============================== Model Call Helper ================================
def call_model(model_name, system_prompt, user_prompt, max_tokens=120):
    try:
        client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
            timeout=180.0
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            max_tokens=max_tokens,
            temperature=0.1
        )

        content = response.choices[0].message.content

        if content and content.strip():
            return content.strip(), None

        return "No response generated.", None

    except Exception as exc:
        return None, (
            f"{model_name} unavailable or timed out ({exc})"
        )


# ========================== Implementation & Review Agents ===========================

def load_prompt(filename):
    prompt_path = PROMPT_DIR / filename
    return prompt_path.read_text(encoding="utf-8").strip()


def get_implementation_agent_advice(observe_message):
    implementation_prompt = load_prompt(
        "implementation_task_prompt.txt"
    ).replace("{{VALIDATION_EVIDENCE}}", observe_message)

    system_prompt = load_prompt("implementation_system_prompt.txt")

    return call_model(
        IMPLEMENTATION_MODEL,
        system_prompt,
        implementation_prompt,
        max_tokens=120
    )


def get_review_agent_advice(implementation_message, observe_message):
    review_task_prompt = (
        load_prompt("review_task_prompt.txt")
        .replace("{{IMPLEMENTATION_RECOMMENDATION}}", implementation_message)
        .replace("{{VALIDATION_EVIDENCE}}", observe_message)
    )

    system_prompt = load_prompt("review_system_prompt.txt")

    return call_model(
        REVIEW_MODEL,
        system_prompt,
        review_task_prompt,
        max_tokens=150
    )


# =============================== Human Review & Adapt ================================
def human_review():
    print()
    print("HUMAN REVIEW")
    print("1 - Accept")
    print("2 - Partially Accept")
    print("3 - Reject")

    decision = input("Decision: ").strip()

    if decision == "1":
        return "Accept"

    if decision == "2":
        return "Partially Accept"

    return "Reject"


def adapt(decision):
    print()

    if decision == "Accept":
        print(
            "ADAPT: Apply recommendation and rerun validation."
        )

    elif decision == "Partially Accept":
        print(
            "ADAPT: Apply selected recommendations and "
            "rerun validation."
        )

    else:
        print(
            "ADAPT: Keep current implementation and "
            "document rationale."
        )


# ================================= Main / Loop Entry ================================
def main():
    print("=" * 60)
    print("ASD USER MANAGEMENT AGENTIC LOOP")
    print("=" * 60)

    print()
    print("PLAN")
    print(PLAN)

    print()
    print("ACT")
    print("Check local database records")

    print()
    print("OBSERVE: Database Check")
    ok_data, msg_data = observe_data_quality()
    print(msg_data)

    print()
    print("OBSERVE: Uniqueness Check")
    ok_unique, msg_unique = observe_uniqueness()
    print(msg_unique)

    sample_user = get_sample_user()

    print()
    print("OBSERVE: Live Endpoint Check")
    live_results = observe_live_endpoints(sample_user)

    observe_message = (
        f"{msg_data}. "
        f"{msg_unique}. "
        f"Live endpoint checks: " + "; ".join(live_results)
    )

    print()
    print("IMPLEMENTATION AGENT")
    print(f"Model: {IMPLEMENTATION_MODEL}")

    implementation_advice, implementation_error = (
        get_implementation_agent_advice(
            observe_message
        )
    )

    if implementation_advice:
        print()
        print(implementation_advice)
    else:
        print()
        print(implementation_error)
        implementation_advice = (
            "Implementation agent unavailable."
        )

    print()
    print("REVIEW AGENT")
    print(f"Model: {REVIEW_MODEL}")

    review_advice, review_error = (
        get_review_agent_advice(
            implementation_advice,
            observe_message
        )
    )

    if review_advice:
        print()
        print(review_advice)
    else:
        print()
        print(review_error)

    print()
    print("HUMAN DECISION")

    decision = human_review()

    print()
    print(f"Decision: {decision}")

    adapt(decision)

    print()
    print("LOOP COMPLETE")


if __name__ == "__main__":
    main()