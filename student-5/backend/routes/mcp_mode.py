from flask import Blueprint, jsonify
from services.mcp_client import call_mcp_tool
from flask import request
import os
mcp_mode_bp = Blueprint("mcp_mode", __name__)

MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"
@mcp_mode_bp.get("/mcp/transactions")
def mcp_list_transactions():
    if not MCP_ENABLED:
        return jsonify({"error": "MCP is disabled in this environment"}), 403
    account_id = request.args.get("account_id", type=int)
    return jsonify(call_mcp_tool("transactions_list", {"account_id": account_id}))


@mcp_mode_bp.get("/mcp/transactions/<int:transaction_id>")
def mcp_get_transaction(transaction_id):
    if not MCP_ENABLED:
        return jsonify({"error": "MCP is disabled in this environment"}), 403
    return jsonify(call_mcp_tool("transaction_detail", {"transaction_id": transaction_id}))


@mcp_mode_bp.get("/mcp/accounts/<int:account_id>/summary")
def mcp_account_summary(account_id):
    if not MCP_ENABLED:
        return jsonify({"error": "MCP is disabled in this environment"}), 403
    return jsonify(call_mcp_tool("account_activity_summary", {"account_id": account_id}))