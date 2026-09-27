import json
from flask import Blueprint, jsonify, request

from services.mcp_client import call_mcp_tool
from services.database_api import get_cards

mcp_mode_bp = Blueprint("mcp_mode", __name__)


def mcp_mode_is_enabled(req) -> bool:
    enabled = __import__("os").getenv("MCP_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
    if not enabled:
        return False

    mode_header = req.headers.get("X-MCP-Mode", "on").strip().lower()
    return mode_header in ("1", "true", "yes", "on")


def mcp_disabled_response():
    return "<p>MCP Mode is disabled.</p>", 403


def mcp_render_json(title: str, payload) -> str:
    return f"<h3>{title}</h3><pre>{json.dumps(payload, indent=2)}</pre>"


@mcp_mode_bp.get("/mcp")
def health():
    return "<p>mcp is running</p>", 200


@mcp_mode_bp.get("/mcp/card-count")
def mcp_card_count():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()

    try:
        result = call_mcp_tool("card_count")
        if isinstance(result, dict) and "error" in result:
            return mcp_render_json("MCP Tool: card count (error)", result), 503
        return mcp_render_json("MCP Tool: card count", result), 200
    except Exception as exc:
        return (
            "<p>MCP card count failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@mcp_mode_bp.post("/mcp/card-per-user")
def mcp_card_per_user():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()

    raw_user_id = request.form.get("card_per_user_id", "").strip()
    if not raw_user_id:
        return "<p>user_id is required.</p>", 400

    try:
        user_id = int(raw_user_id)
    except ValueError:
        return "<p>user_id must be a number.</p>", 400

    try:
        result = call_mcp_tool("card_per_user", {"user_id": user_id})
        if isinstance(result, dict) and "error" in result:
            return mcp_render_json("MCP Tool: card per user (error)", result), 503
        return mcp_render_json("MCP Tool: card per user", result), 200
    except Exception as exc:
        return (
            "<p>MCP card per user failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )