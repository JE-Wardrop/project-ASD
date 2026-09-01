from flask import Blueprint, request
import requests

from services.database_api import (
    adjust_balance_response,
    close_account_response,
    create_account_response,
    delete_account_response,
    freeze_account_response,
    get_account_balance_response,
    get_account_response,
    get_accounts,
    get_accounts_by_status_response,
    get_accounts_by_user_response,
    unfreeze_account_response,
    update_account_response,
)
from views.html_formatters import format_account_html, format_accounts_html, format_balance_html

normal_ui_bp = Blueprint("normal_ui", __name__)


@normal_ui_bp.get("/")
def health():
    return "<p>account-service running</p>", 200


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

@normal_ui_bp.get("/accounts")
def get_accounts_route():
    try:
        return format_accounts_html(get_accounts()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve accounts from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/accounts/by-id")
def get_account_by_id():
    account_id = request.args.get("account_id", "").strip()

    if not account_id:
        return "<p>Account ID is required.</p>", 400

    try:
        response = get_account_response(account_id)

        if response.status_code == 404:
            return "<p>Account not found.</p>", 404

        response.raise_for_status()
        return format_account_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve account from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/accounts/by-user")
def get_accounts_by_user():
    user_id = request.args.get("user_id", "").strip()

    if not user_id:
        return "<p>User ID is required.</p>", 400

    try:
        response = get_accounts_by_user_response(user_id)

        if response.status_code == 404:
            return f"<p>No accounts found for user {user_id}.</p>", 404

        response.raise_for_status()
        return format_accounts_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve accounts from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/accounts/by-status")
def get_accounts_by_status():
    status = request.args.get("status", "").strip().upper()

    if not status:
        return "<p>Status is required.</p>", 400

    try:
        response = get_accounts_by_status_response(status)

        if response.status_code == 404:
            return f"<p>No accounts found with status {status}.</p>", 404
        if response.status_code == 400:
            return f"<p>{response.json().get('error', 'Invalid status.')}</p>", 400

        response.raise_for_status()
        return format_accounts_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve accounts from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/accounts/balance")
def get_account_balance():
    account_id = request.args.get("account_id", "").strip()

    if not account_id:
        return "<p>Account ID is required.</p>", 400

    try:
        response = get_account_balance_response(account_id)

        if response.status_code == 404:
            return "<p>Account not found.</p>", 404

        response.raise_for_status()
        return format_balance_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve balance from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@normal_ui_bp.post("/accounts/create")
def create_account():
    payload = {
        "user_id": request.form.get("user_id", "").strip(),
        "account_number": request.form.get("account_number", "").strip(),
        "account_type": request.form.get("account_type", "").strip().upper(),
        "balance": request.form.get("balance", "0").strip() or "0",
    }

    try:
        response = create_account_response(payload)

        if response.status_code in (400, 409):
            return f"<p>{response.json().get('error', 'Invalid account data.')}</p>", response.status_code

        response.raise_for_status()
        return format_account_html(response.json()), 201
    except requests.RequestException as exc:
        return (
            "<p>Failed to create account in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@normal_ui_bp.post("/accounts/update")
def update_account():
    account_id = request.form.get("account_id", "").strip()

    if not account_id:
        return "<p>Account ID is required.</p>", 400

    payload = {}
    account_number = request.form.get("account_number", "").strip()
    account_type = request.form.get("account_type", "").strip().upper()

    if account_number:
        payload["account_number"] = account_number
    if account_type:
        payload["account_type"] = account_type

    if not payload:
        return "<p>At least one field to update is required.</p>", 400

    try:
        response = update_account_response(account_id, payload)

        if response.status_code == 404:
            return "<p>Account not found.</p>", 404
        if response.status_code in (400, 409):
            return f"<p>{response.json().get('error', 'Invalid update.')}</p>", response.status_code

        response.raise_for_status()
        return format_account_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to update account in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


# ---------------------------------------------------------------------------
# Balance adjustment (deposit / withdraw)
# ---------------------------------------------------------------------------

@normal_ui_bp.post("/accounts/adjust-balance")
def adjust_balance():
    account_id = request.form.get("account_id", "").strip()
    delta_raw = request.form.get("delta", "").strip()

    if not account_id or not delta_raw:
        return "<p>Account ID and amount are required.</p>", 400

    try:
        delta = float(delta_raw)
    except ValueError:
        return "<p>Amount must be a number.</p>", 400

    try:
        response = adjust_balance_response(account_id, delta)

        if response.status_code == 404:
            return "<p>Account not found.</p>", 404
        if response.status_code in (400, 409):
            return f"<p>{response.json().get('error', 'Unable to adjust balance.')}</p>", response.status_code

        response.raise_for_status()
        return format_balance_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to adjust balance in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

@normal_ui_bp.post("/accounts/freeze")
def freeze_account():
    account_id = request.form.get("account_id", "").strip()

    if not account_id:
        return "<p>Account ID is required.</p>", 400

    try:
        response = freeze_account_response(account_id)

        if response.status_code == 404:
            return "<p>Account not found.</p>", 404
        if response.status_code == 409:
            return f"<p>{response.json().get('error', 'Cannot freeze account.')}</p>", 409

        response.raise_for_status()
        return format_account_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to freeze account in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/accounts/unfreeze")
def unfreeze_account():
    account_id = request.form.get("account_id", "").strip()

    if not account_id:
        return "<p>Account ID is required.</p>", 400

    try:
        response = unfreeze_account_response(account_id)

        if response.status_code == 404:
            return "<p>Account not found.</p>", 404
        if response.status_code == 409:
            return f"<p>{response.json().get('error', 'Cannot unfreeze account.')}</p>", 409

        response.raise_for_status()
        return format_account_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to unfreeze account in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/accounts/close")
def close_account():
    account_id = request.form.get("account_id", "").strip()

    if not account_id:
        return "<p>Account ID is required.</p>", 400

    try:
        response = close_account_response(account_id)

        if response.status_code == 404:
            return "<p>Account not found.</p>", 404
        if response.status_code == 409:
            return f"<p>{response.json().get('error', 'Cannot close account.')}</p>", 409

        response.raise_for_status()
        return format_account_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to close account in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


# ---------------------------------------------------------------------------
# DELETE (hard delete, demo/testing only)
# ---------------------------------------------------------------------------

@normal_ui_bp.post("/accounts/delete")
def delete_account():
    account_id = request.form.get("account_id", "").strip()

    if not account_id:
        return "<p>Account ID is required.</p>", 400

    try:
        response = delete_account_response(account_id)

        if response.status_code == 404:
            return "<p>Account not found.</p>", 404

        response.raise_for_status()
        return f"<p>Account #{account_id} deleted.</p>", 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to delete account in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )
