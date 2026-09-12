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

mcp_bp = Blueprint("mcp_mode", __name__)


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


@mcp_bp.post("/mcp/card-sount")
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


# @mcp_bp.post("/mcp/students-by-subject")
# def mcp_students_by_subject():
#     if not mcp_mode_is_enabled(request):
#         return mcp_disabled_response()

#     subject_code = request.form.get("subject_code", "").strip().upper()
#     if not subject_code:
#         return "<p>subject_code is required.</p>", 400

#     try:
#         response = get_students_by_subject_response(subject_code)

#         if response.status_code == 404:
#             return mcp_render_json("MCP Tool: students_by_subject", []), 200

#         response.raise_for_status()
#         return mcp_render_json("MCP Tool: students_by_subject", response.json()), 200
#     except requests.RequestException as exc:
#         return (
#             "<p>MCP students_by_subject failed.</p>"
#             f"<pre>{exc}</pre>",
#             503,
#         )


# @mcp_bp.post("/mcp/project-files")
# def mcp_project_files():
#     if not mcp_mode_is_enabled(request):
#         return mcp_disabled_response()

#     directory_path = request.form.get("directory_path", "..").strip()
#     path = (APP_DIR / directory_path).resolve()

#     if not path.exists() or not path.is_dir():
#         return mcp_render_json(
#             "MCP Tool: project_files",
#             {"error": f"Directory not found: {path}"},
#         ), 400

#     items = sorted(item.name for item in path.iterdir())
#     return mcp_render_json("MCP Tool: project_files", items), 200


# @mcp_bp.post("/mcp/ci-report")
# def mcp_ci_report():
#     if not mcp_mode_is_enabled(request):
#         return mcp_disabled_response()

#     report_path = request.form.get("report_path", "../reports/report.json").strip()
#     report_file = (BASE_DIR / report_path).resolve()

#     if not report_file.exists():
#         return mcp_render_json(
#             "MCP Tool: ci_report",
#             {
#                 "error": "Report not found",
#                 "path": str(report_file),
#                 "hint": "Run Lab 05 workflow_dispatch to generate report.json",
#             },
#         ), 404

#     try:
#         with report_file.open("r", encoding="utf-8") as file:
#             payload = json.load(file)
#         return mcp_render_json("MCP Tool: ci_report", payload), 200
#     except Exception as exc:
#         return (
#             "<p>MCP ci_report failed.</p>"
#             f"<pre>{exc}</pre>",
#             500,
#         )