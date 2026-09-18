import json
from pathlib import Path

from flask import Blueprint, request
import requests

from services.database_api import (
    create_card_response,
    delete_card_response,
    get_cards,
    update_card_response,
    get_card_by_id_response,
    get_cards_by_type_response,
    freeze_card_response,
    unfreeze_card_response,
)
from views.html_formatters import format_card_html, format_cards_html



BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR.parent

mcp_mode_bp = Blueprint("mcp_mode", __name__)



def mcp_mode_is_enabled(req) -> bool:
    import os

    enabled = os.getenv("MCP_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
    if not enabled:
        return False

    mode_header = req.headers.get("X-MCP-Mode", "on").strip().lower()
    return mode_header in ("1", "true", "yes", "on")


def mcp_disabled_response():
    return "<p>MCP Mode is disabled.</p>", 403


def mcp_render_json(title: str, payload):
    return f"<h3>{title}</h3><pre>{json.dumps(payload, indent=2)}</pre>"


@mcp_mode_bp.get("/mcp")
def health():
    return "<p>mcp is running</p>", 200


@mcp_mode_bp.post("/mcp/card-count")
def mcp_card_count():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()

    try:
        count = len(get_cards())
        return mcp_render_json("MCP Tool: card count", {"card_count": count}), 200
    except requests.RequestException as exc:
        return (
            "<p>MCP card count failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )
    
@mcp_mode_bp.post("/mcp/card-per-user")
def mcp_card_per_user():
    if not mcp_mode_is_enabled(request):
        return mcp_disabled_response()

    try:
        count = len(get_cards())
        return mcp_render_json("MCP Tool: card count", {"card_count": count}), 200
    except requests.RequestException as exc:
        return (
            "<p>MCP card count failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )

    
