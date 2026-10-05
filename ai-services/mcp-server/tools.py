"""MCP tools — call each feature's database API over HTTP.
 
Rule this file exists to enforce (Release 0 architecture invariant,
Cross-Feature Database API Integration): no tool opens another feature's
.db file directly. Every tool goes through that feature's exposed HTTP
API, the same way student-5/backend/services/accounts_api.py already
calls http://student2-database:5002 for the balance-adjustment endpoint.
 
The MCP server runs on the host (not in Docker), and docker-compose.yml
already publishes each database service on a host port, so tools call
"localhost:<port>" directly — no host.docker.internal needed here; that
mapping is only for container -> host calls, not host -> container.
"""
 
import os
 
import requests
 
# One base URL per feature's database API
DB_API_URLS = {
    1: os.getenv("STUDENT1_DB_URL", "http://localhost:8301"),  # Cards
    2: os.getenv("STUDENT2_DB_URL", "http://localhost:8302"),  # Accounts
    3: os.getenv("STUDENT3_DB_URL", "http://localhost:8303"),  # Notifications
    4: os.getenv("STUDENT4_DB_URL", "http://localhost:8304"),  # Users
    5: os.getenv("STUDENT5_DB_URL", "http://localhost:8305"),  # Transactions
}
 
REQUEST_TIMEOUT = 5  # seconds — a tool must fail fast, not hang the server

 
def _get(base_url: str, path: str, params: dict | None = None) -> dict:
    """Shared HTTP GET helper. Never raises — returns a structured error
    dict instead, so a bad call surfaces as a tool result, not a crash.
    """
    try:
        resp = requests.get(f"{base_url}{path}", params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Database API unreachable at {base_url}. Is the container running?"}
    except requests.exceptions.Timeout:
        return {"error": f"Database API at {base_url} did not respond in {REQUEST_TIMEOUT}s"}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"Database API returned {resp.status_code}", "detail": str(exc)}
 

# def list_project_files(directory_path: str = ".."):  # relative to mcp-server/
#     path = (BASE_DIR / directory_path).resolve()
#     if not path.exists() or not path.is_dir():
#         return {"error": f"Directory not found: {path}"}

#     return sorted(item.name for item in path.iterdir())


# def read_ci_report(report_path: str = "../reports/report.json"):
#     report_file = (BASE_DIR / report_path).resolve()
#     if not report_file.exists():
#         return {
#             "error": "Report not found",
#             "path": str(report_file),
#             "hint": "Run Lab 05 workflow_dispatch to generate report.json",
#         }

#     with report_file.open("r", encoding="utf-8") as file:
#         return json.load(file)



# Student 1 (Card Management) 
# database API (student-1/database/app.py: GET /cards, GET /cards/<id>, GET /cards/by-type, GET /cards/by-status, POST /cards/create, PUT /cards/<id>, DELETE /cards/<id>, POST /cards/freeze, POST /cards/unfreeze)

def get_card_count() -> dict:
    cards = _get(DB_API_URLS[1], "/cards")
    if isinstance(cards, dict) and "error" in cards:
        return cards
    return {"card_count": len(cards)}


def get_card_per_user(user_id: int) -> dict:
    cards = _get(DB_API_URLS[1], "/cards")
    if isinstance(cards, dict) and "error" in cards:
        return cards
    matching = [c for c in cards if c.get("user_id") == user_id]
    return {"user_id": user_id, "card_count": len(matching), "cards": matching}
    
    


# Transaction Management (student-5)
# student-5/database/app.py: GET /transactions, GET /transactions/<id>

VALID_TXN_TYPES = {"DEPOSIT", "WITHDRAWAL", "TRANSFER"}
VALID_TXN_STATUSES = {"PENDING", "COMPLETED", "FAILED", "CANCELLED"}
 
 
def list_transactions(
    account_id: int | None = None,
    transaction_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> dict:
    """List transactions, optionally filtered by account, type or status.
 
    account_id matches either the sender or the receiver side.
    """
    if transaction_type is not None and transaction_type.upper() not in VALID_TXN_TYPES:
        return {"error": f"transaction_type must be one of {sorted(VALID_TXN_TYPES)}"}
    
    if status is not None and status.upper() not in VALID_TXN_STATUSES:
        return {"error": f"status must be one of {sorted(VALID_TXN_STATUSES)}"}
 
    params = {
        "account_id": account_id,
        "type": transaction_type,
        "status": status,
        "limit": max(1, min(limit, 100)),
    }
    # Drop unset filters instead of sending them as the string "None"
    params = {k: v for k, v in params.items() if v is not None}
 
    return _get(DB_API_URLS[5], "/transactions", params=params)
 
 
def get_transaction(transaction_id: int) -> dict:
    """Fetch a single transaction by its id."""
    return _get(DB_API_URLS[5], f"/transactions/{transaction_id}")
 
 
def summarize_account_activity(account_id: int) -> dict:
    """Aggregate a snapshot of an account's transaction activity.
 
    All arithmetic happens here in Python, not in the LLM (NFR-02: the
    model never computes money) — this tool hands the model finished
    numbers to narrate, not raw rows to add up itself.
    """
    result = list_transactions(account_id=account_id, limit=100)
    if "error" in result:
        return result
 
    transactions = result.get("transactions", [])
    total_in = 0.0
    total_out = 0.0
    by_status: dict[str, int] = {}
 
    for txn in transactions:
        by_status[txn["status"]] = by_status.get(txn["status"], 0) + 1
        if txn["status"] != "COMPLETED":
            continue
        if txn["receiver_account_id"] == account_id:
            total_in += txn["amount"]
        if txn["sender_account_id"] == account_id:
            total_out += txn["amount"]
 
    return {
        "account_id": account_id,
        "transaction_count": len(transactions),
        "total_in": round(total_in, 2),
        "total_out": round(total_out, 2),
        "net": round(total_in - total_out, 2),
        "by_status": by_status,
    }
 


# Bank Account Management (student-2)
# student-2/database/app.py: GET /accounts, GET /accounts/<id>/balance, GET /accounts/by-user
#
# Tool boundary: read-only. Freezing, closing or changing a balance stays in
# the Normal UI where a human confirms it — no MCP tool can move money or
# change an account's status. Full account numbers are masked to the last 4
# digits (same privacy rule as the RAG corpus, which leaves them out).

VALID_ACCOUNT_STATUSES = {"ACTIVE", "FROZEN", "CLOSED"}


def _mask_account_number(account_number) -> str:
    digits = str(account_number or "")
    return f"****{digits[-4:]}" if len(digits) >= 4 else "****"


def get_account_balance(account_id: int) -> dict:
    """Current balance and status of one account."""
    result = _get(DB_API_URLS[2], f"/accounts/{account_id}/balance")
    if "error" in result:
        return result
    return {
        "account_id": result["account_id"],
        "balance": round(result["balance"], 2),
        "account_status": result["account_status"],
        # Only ACTIVE accounts accept balance changes (PATCH /accounts/<id>/balance)
        "can_transact": result["account_status"] == "ACTIVE",
    }


def list_accounts_by_user(user_id: int) -> dict:
    """Every account a user owns, plus totals computed here, not by the LLM."""
    result = _get(DB_API_URLS[2], "/accounts/by-user", params={"user_id": user_id})
    # The database API answers 404 when the user owns no accounts; that is a
    # valid empty result for this tool, not a failure.
    if isinstance(result, dict) and "error" in result:
        if result["error"] == "Database API returned 404":
            return {"user_id": user_id, "account_count": 0, "total_balance": 0.0, "accounts": []}
        return result

    accounts = [
        {
            "account_id": acc["account_id"],
            "account_number": _mask_account_number(acc["account_number"]),
            "account_type": acc["account_type"],
            "account_status": acc["account_status"],
            "balance": round(acc["balance"], 2),
        }
        for acc in result
    ]
    return {
        "user_id": user_id,
        "account_count": len(accounts),
        "total_balance": round(sum(acc["balance"] for acc in accounts), 2),
        "accounts": accounts,
    }


def summarize_account_statuses(status: str | None = None) -> dict:
    """Counts and balance totals per status and per type across all accounts.

    Optional `status` narrows the summary to ACTIVE, FROZEN or CLOSED.
    """
    if status is not None and status.upper() not in VALID_ACCOUNT_STATUSES:
        return {"error": f"status must be one of {sorted(VALID_ACCOUNT_STATUSES)}"}

    accounts = _get(DB_API_URLS[2], "/accounts")
    if isinstance(accounts, dict) and "error" in accounts:
        return accounts

    if status is not None:
        accounts = [acc for acc in accounts if acc["account_status"] == status.upper()]

    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    balance_by_status: dict[str, float] = {}

    for acc in accounts:
        by_status[acc["account_status"]] = by_status.get(acc["account_status"], 0) + 1
        by_type[acc["account_type"]] = by_type.get(acc["account_type"], 0) + 1
        balance_by_status[acc["account_status"]] = (
            balance_by_status.get(acc["account_status"], 0.0) + acc["balance"]
        )

    return {
        "status_filter": status.upper() if status else None,
        "account_count": len(accounts),
        "by_status": by_status,
        "by_type": by_type,
        "balance_by_status": {k: round(v, 2) for k, v in balance_by_status.items()},
        "total_balance": round(sum(acc["balance"] for acc in accounts), 2),
    }


# ---------------------------------------------------------------------------
# Manual validation — mirrors the lab's "Terminal B" pattern, but every
# call here goes over HTTP, so it only proves something when the actual
# student5-db container (or a local run of student-5/database/app.py) is
# reachable at DB_API_URLS[5].
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    print("DB_API_URLS:", DB_API_URLS)
    print(list_transactions(limit=5))
    print(summarize_account_activity(account_id=1))
    print(get_account_balance(account_id=1))
    print(list_accounts_by_user(user_id=1))
    print(summarize_account_statuses())
 
