"""MCP tab routes: browser -> this backend -> shared MCP server -> accounts DB API.

Every route returns the tool's structured JSON result. All three tools are
read-only; account changes stay in the Normal UI.
"""

import os

from flask import Blueprint, jsonify, request

from services.mcp_client import call_mcp_tool

mcp_mode_bp = Blueprint("mcp_mode", __name__)

# Read once at start-up. CI sets it to "false".
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")


def mcp_mode_is_enabled() -> bool:
    if not MCP_ENABLED:
        return False
    header = request.headers.get("X-MCP-Mode", "on").strip().lower()
    return header in ("1", "true", "yes", "on")


def mcp_disabled_response():
    return jsonify({"error": "MCP is disabled in this environment"}), 403


def to_response(result: dict):
    if "error" not in result:
        return jsonify(result), 200
    # 404: the tool ran but the account does not exist.
    # 502: the MCP server or the database API behind it reported another error.
    return jsonify(result), 404 if result["error"] == "Database API returned 404" else 502


@mcp_mode_bp.get("/mcp/accounts/<int:account_id>/balance")
def mcp_account_balance(account_id):
    if not mcp_mode_is_enabled():
        return mcp_disabled_response()
    return to_response(call_mcp_tool("account_balance", {"account_id": account_id}))


@mcp_mode_bp.get("/mcp/users/<int:user_id>/accounts")
def mcp_accounts_by_user(user_id):
    if not mcp_mode_is_enabled():
        return mcp_disabled_response()
    return to_response(call_mcp_tool("accounts_by_user", {"user_id": user_id}))


@mcp_mode_bp.get("/mcp/accounts/summary")
def mcp_account_status_summary():
    if not mcp_mode_is_enabled():
        return mcp_disabled_response()
    status = request.args.get("status", "").strip().upper() or None
    return to_response(call_mcp_tool("account_status_summary", {"status": status}))
