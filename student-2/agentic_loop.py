"""Agentic loop for the Bank Account Management microservice (student-2).

Demonstrates the PLAN -> ACT -> OBSERVE -> IMPLEMENTATION AGENT ->
REVIEW AGENT -> HUMAN REVIEW -> ADAPT workflow used across the ASD labs,
scoped to the accounts database and the account-service backend.
"""

import os
import sqlite3
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

APP_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=APP_DIR / ".env")

DATABASE_NAME = os.getenv("DB_PATH", str(APP_DIR / "database" / "accounts.db"))
FLASK_BASE_URL = os.getenv("FLASK_BASE_URL", "http://localhost:8202")
PROMPT_DIR = APP_DIR / "prompts" / "service"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
IMPLEMENTATION_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
REVIEW_MODEL = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b")

VALID_ACCOUNT_TYPES = {"EVERYDAY", "SAVINGS"}
VALID_STATUSES = {"ACTIVE", "FROZEN", "CLOSED"}

PLAN = {
    "goal": "Validate the Bank Account Management microservice using a local multi-agent workflow",
    "db_plan": [
        "Check account data quality (>=10 records, valid required fields)",
        "Check account_number uniqueness and account_type/account_status domains",
    ],
    "endpoints_plan": [
        "GET /accounts - list all accounts",
        "GET /accounts/by-id - get one account",
        "GET /accounts/balance - view balance",
        "POST /ask - local AI agent",
    ],
}


# ================================ Observe: Database ================================

def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def observe_data_quality():
    if not os.path.exists(DATABASE_NAME):
        return False, f"Database file not found: {DATABASE_NAME}"

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    accounts = cursor.execute(
        """
        SELECT account_id, user_id, account_number, account_type, balance, account_status
        FROM accounts
        """
    ).fetchall()

    conn.close()

    if len(accounts) < 10:
        return False, f"Expected at least 10 accounts, found {len(accounts)}"

    seen_numbers = set()
    for account_id, user_id, account_number, account_type, balance, status in accounts:
        if not isinstance(user_id, int):
            return False, f"account {account_id}: user_id must be an integer"
        if not account_number:
            return False, f"account {account_id}: account_number is required"
        if account_number in seen_numbers:
            return False, f"account {account_id}: duplicate account_number {account_number}"
        seen_numbers.add(account_number)
        if account_type not in VALID_ACCOUNT_TYPES:
            return False, f"account {account_id}: invalid account_type {account_type}"
        if status not in VALID_STATUSES:
            return False, f"account {account_id}: invalid account_status {status}"
        if balance < 0:
            return False, f"account {account_id}: negative balance {balance}"

    return True, (
        f"Database evidence: {len(accounts)} accounts, all account_numbers unique, "
        "account_type and account_status within domain, no negative balances."
    )


def get_sample_account():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT account_id, account_status FROM accounts WHERE account_status = 'ACTIVE' LIMIT 1"
    ).fetchone()
    conn.close()
    return row


# ============================= Observe: Live Endpoints ==============================

def observe_live_endpoints(sample_account):
    results = []
    account_id = sample_account[0] if sample_account else None

    def check(label, method, url, **kwargs):
        try:
            response = requests.request(method, url, timeout=5, **kwargs)
            content_ok = bool(response.text and response.text.strip())
            line = f"{label} -> HTTP {response.status_code}, content_ok={content_ok}"
        except Exception as exc:
            line = f"{label} -> error: {exc}"

        print(f"  Checked {line}")
        results.append(line)

    check("GET /accounts", "GET", f"{FLASK_BASE_URL}/accounts")

    if account_id is not None:
        check(
            "GET /accounts/by-id",
            "GET",
            f"{FLASK_BASE_URL}/accounts/by-id?account_id={account_id}",
        )
        check(
            "GET /accounts/balance",
            "GET",
            f"{FLASK_BASE_URL}/accounts/balance?account_id={account_id}",
        )
    else:
        skipped = "GET /accounts/by-id and /accounts/balance -> skipped: no ACTIVE sample account found"
        print(f"  Checked {skipped}")
        results.append(skipped)

    check(
        "POST /ask",
        "POST",
        f"{FLASK_BASE_URL}/ask",
        data={"question": "What does the account service do?"},
    )

    return results


# =============================== Model Call Helper ================================

def call_model(model_name, system_prompt, user_prompt, max_tokens=150):
    try:
        client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=180.0)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip(), None

        return "No response generated.", None

    except Exception as exc:
        return None, f"{model_name} unavailable or timed out ({exc})"


# ======================== Implementation & Review Agents ===========================

def get_implementation_agent_advice(observe_message):
    system_prompt = load_prompt("implementation/system_prompt.txt")
    task_prompt = load_prompt("implementation/task_prompt.txt")

    task_prompt = task_prompt.replace("{{REVIEW_TARGET}}", "Account Management")
    task_prompt = task_prompt.replace("{{VALIDATION_EVIDENCE}}", observe_message)

    return call_model(IMPLEMENTATION_MODEL, system_prompt, task_prompt, max_tokens=120)


def get_review_agent_advice(implementation_message, observe_message):
    review_prompt = load_prompt("review/agent_review_prompt.txt")

    user_prompt = (
        f"Implementation Recommendation:\n{implementation_message}\n\n"
        f"Validation Evidence:\n{observe_message}\n"
    )

    return call_model(REVIEW_MODEL, review_prompt, user_prompt, max_tokens=120)


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
        print("ADAPT: Apply recommendation and rerun validation.")
    elif decision == "Partially Accept":
        print("ADAPT: Apply selected recommendations and rerun validation.")
    else:
        print("ADAPT: Keep current implementation and document rationale.")


# ================================= Main / Loop Entry ================================

def main():
    print("=" * 60)
    print("STUDENT-2 AGENTIC LOOP - BANK ACCOUNT MANAGEMENT")
    print("=" * 60)

    print()
    print("PLAN")
    print(PLAN)

    print()
    print("ACT")
    print("Check local accounts database and live account-service endpoints")

    print()
    print("OBSERVE: Database Check")
    ok_data, msg_data = observe_data_quality()
    print(msg_data)

    sample_account = get_sample_account()

    print()
    print("OBSERVE: Live Endpoint Check")
    live_results = observe_live_endpoints(sample_account)

    observe_message = f"{msg_data}. Live endpoint checks: " + "; ".join(live_results)

    print()
    print("IMPLEMENTATION AGENT")
    print(f"Model: {IMPLEMENTATION_MODEL}")

    implementation_advice, implementation_error = get_implementation_agent_advice(observe_message)

    if implementation_advice:
        print()
        print(implementation_advice)
    else:
        print()
        print(implementation_error)
        implementation_advice = "Implementation agent unavailable."

    print()
    print("REVIEW AGENT")
    print(f"Model: {REVIEW_MODEL}")

    review_advice, review_error = get_review_agent_advice(implementation_advice, observe_message)

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
