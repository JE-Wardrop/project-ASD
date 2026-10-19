import os
import re
import sqlite3

from flask import Flask, jsonify, request
from init_db import DATABASE_NAME, VALID_ACCOUNT_TYPES, VALID_STATUSES, init_db

app = Flask(__name__)

ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{8}$")

# Lab 11 (Ruff S608): every query is a complete literal string with "?" placeholders,
# so no SQL is built with f-strings or string concatenation.
SELECT_ACCOUNTS = (
    "SELECT account_id, user_id, account_number, account_type, "
    "balance, account_status, created_at FROM accounts"
)
SELECT_ACCOUNT_BY_ID = (
    "SELECT account_id, user_id, account_number, account_type, "
    "balance, account_status, created_at FROM accounts WHERE account_id = ?"
)
SELECT_ACCOUNTS_BY_USER = (
    "SELECT account_id, user_id, account_number, account_type, "
    "balance, account_status, created_at FROM accounts WHERE user_id = ?"
)
SELECT_ACCOUNTS_BY_STATUS = (
    "SELECT account_id, user_id, account_number, account_type, "
    "balance, account_status, created_at FROM accounts WHERE account_status = ?"
)
# NULL keeps the current value, so one fixed statement covers every field combination.
UPDATE_ACCOUNT_INFO = (
    "UPDATE accounts SET account_number = COALESCE(?, account_number), "
    "account_type = COALESCE(?, account_type) WHERE account_id = ?"
)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row) if row is not None else None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/")
def health():
    return jsonify({"service": "student2-database", "status": "running"})


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

@app.get("/accounts")
def get_accounts():
    conn = get_db_connection()
    accounts = conn.execute(SELECT_ACCOUNTS).fetchall()
    conn.close()
    return jsonify([row_to_dict(row) for row in accounts])


@app.get("/accounts/<int:account_id>")
def get_account(account_id):
    conn = get_db_connection()
    account = conn.execute(SELECT_ACCOUNT_BY_ID, (account_id,)).fetchone()
    conn.close()

    if account is None:
        return jsonify({"error": "Account not found"}), 404

    return jsonify(row_to_dict(account))


@app.get("/accounts/by-user")
def get_accounts_by_user():
    user_id = request.args.get("user_id", type=int)

    if user_id is None:
        return jsonify({"error": "user_id required"}), 400

    conn = get_db_connection()
    accounts = conn.execute(SELECT_ACCOUNTS_BY_USER, (user_id,)).fetchall()
    conn.close()

    if not accounts:
        return jsonify({"error": "No accounts found"}), 404

    return jsonify([row_to_dict(row) for row in accounts])


@app.get("/accounts/by-status")
def get_accounts_by_status():
    status = request.args.get("status", "").strip().upper()

    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {VALID_STATUSES}"}), 400

    conn = get_db_connection()
    accounts = conn.execute(SELECT_ACCOUNTS_BY_STATUS, (status,)).fetchall()
    conn.close()

    if not accounts:
        return jsonify({"error": "No accounts found"}), 404

    return jsonify([row_to_dict(row) for row in accounts])


@app.get("/accounts/<int:account_id>/balance")
def get_account_balance(account_id):
    conn = get_db_connection()
    account = conn.execute(
        "SELECT account_id, balance, account_status FROM accounts WHERE account_id = ?",
        (account_id,),
    ).fetchone()
    conn.close()

    if account is None:
        return jsonify({"error": "Account not found"}), 404

    return jsonify(row_to_dict(account))


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@app.post("/accounts")
def create_account():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    account_number = str(data.get("account_number") or "").strip()
    account_type = str(data.get("account_type") or "").strip().upper()
    balance = data.get("balance", 0.0)

    if user_id is None or not account_number or not account_type:
        return jsonify({"error": "user_id, account_number and account_type are required"}), 400

    if not ACCOUNT_NUMBER_PATTERN.match(account_number):
        return jsonify({"error": "account_number must be exactly 8 digits"}), 400

    if account_type not in VALID_ACCOUNT_TYPES:
        return jsonify({"error": f"account_type must be one of {VALID_ACCOUNT_TYPES}"}), 400

    try:
        balance = float(balance)
    except (TypeError, ValueError):
        return jsonify({"error": "balance must be a number"}), 400

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO accounts (user_id, account_number, account_type, balance, account_status)
            VALUES (?, ?, ?, ?, 'ACTIVE')
            """,
            (user_id, account_number, account_type, balance),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "account_number already exists"}), 409

    account = conn.execute(SELECT_ACCOUNT_BY_ID, (new_id,)).fetchone()
    conn.close()

    return jsonify(row_to_dict(account)), 201


# ---------------------------------------------------------------------------
# UPDATE (account information: account_number, account_type)
# ---------------------------------------------------------------------------

@app.put("/accounts/<int:account_id>")
def update_account(account_id):
    data = request.get_json(silent=True) or {}

    account_number = None
    account_type = None

    if "account_number" in data:
        account_number = str(data["account_number"]).strip()
        if not ACCOUNT_NUMBER_PATTERN.match(account_number):
            return jsonify({"error": "account_number must be exactly 8 digits"}), 400

    if "account_type" in data:
        account_type = str(data["account_type"]).strip().upper()
        if account_type not in VALID_ACCOUNT_TYPES:
            return jsonify({"error": f"account_type must be one of {VALID_ACCOUNT_TYPES}"}), 400

    if account_number is None and account_type is None:
        return jsonify({"error": "At least one of account_number, account_type is required"}), 400

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT account_id FROM accounts WHERE account_id = ?", (account_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Account not found"}), 404

    try:
        conn.execute(UPDATE_ACCOUNT_INFO, (account_number, account_type, account_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "account_number already exists"}), 409

    account = conn.execute(SELECT_ACCOUNT_BY_ID, (account_id,)).fetchone()
    conn.close()

    return jsonify(row_to_dict(account))


# ---------------------------------------------------------------------------
# Balance adjustment (used internally and by the Transactions microservice)
# ---------------------------------------------------------------------------

@app.patch("/accounts/<int:account_id>/balance")
def adjust_account_balance(account_id):
    data = request.get_json(silent=True) or {}

    try:
        delta = float(data.get("delta"))
    except (TypeError, ValueError):
        return jsonify({"error": "delta is required and must be a number"}), 400

    conn = get_db_connection()
    account = conn.execute(
        "SELECT account_id, balance, account_status FROM accounts WHERE account_id = ?",
        (account_id,),
    ).fetchone()

    if account is None:
        conn.close()
        return jsonify({"error": "Account not found"}), 404

    if account["account_status"] != "ACTIVE":
        conn.close()
        return jsonify({"error": f"Account is {account['account_status']}, balance cannot change"}), 409

    new_balance = account["balance"] + delta
    if new_balance < 0:
        conn.close()
        return jsonify({"error": "Insufficient funds"}), 400

    conn.execute(
        "UPDATE accounts SET balance = ? WHERE account_id = ?", (new_balance, account_id)
    )
    conn.commit()
    updated = conn.execute(SELECT_ACCOUNT_BY_ID, (account_id,)).fetchone()
    conn.close()

    return jsonify(row_to_dict(updated))


# ---------------------------------------------------------------------------
# Status transitions: freeze / unfreeze / close
# ---------------------------------------------------------------------------

def _set_status(account_id, new_status, allowed_from):
    conn = get_db_connection()
    account = conn.execute(
        "SELECT account_id, account_status FROM accounts WHERE account_id = ?",
        (account_id,),
    ).fetchone()

    if account is None:
        conn.close()
        return None, (jsonify({"error": "Account not found"}), 404)

    if account["account_status"] not in allowed_from:
        conn.close()
        return None, (
            jsonify({"error": f"Cannot move account from {account['account_status']} to {new_status}"}),
            409,
        )

    conn.execute(
        "UPDATE accounts SET account_status = ? WHERE account_id = ?",
        (new_status, account_id),
    )
    conn.commit()
    updated = conn.execute(SELECT_ACCOUNT_BY_ID, (account_id,)).fetchone()
    conn.close()

    return row_to_dict(updated), None


@app.post("/accounts/<int:account_id>/freeze")
def freeze_account(account_id):
    account, error = _set_status(account_id, "FROZEN", allowed_from={"ACTIVE"})
    if error:
        return error
    return jsonify(account)


@app.post("/accounts/<int:account_id>/unfreeze")
def unfreeze_account(account_id):
    account, error = _set_status(account_id, "ACTIVE", allowed_from={"FROZEN"})
    if error:
        return error
    return jsonify(account)


@app.post("/accounts/<int:account_id>/close")
def close_account(account_id):
    account, error = _set_status(account_id, "CLOSED", allowed_from={"ACTIVE", "FROZEN"})
    if error:
        return error
    return jsonify(account)


# ---------------------------------------------------------------------------
# DELETE (hard delete, mainly for tests/demo cleanup)
# ---------------------------------------------------------------------------

@app.delete("/accounts/<int:account_id>")
def delete_account(account_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT account_id FROM accounts WHERE account_id = ?", (account_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Account not found"}), 404

    conn.execute("DELETE FROM accounts WHERE account_id = ?", (account_id,))
    conn.commit()
    conn.close()

    return jsonify({"deleted": account_id})


if __name__ == "__main__":
    init_db()
    # Lab 11 (Ruff S201): debug mode is opt-in through FLASK_DEBUG instead of always on.
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(
        host="0.0.0.0",  # noqa: S104 - container needs to bind all interfaces
        port=int(os.environ.get("PORT", 5002)),
        debug=debug_mode,
    )
