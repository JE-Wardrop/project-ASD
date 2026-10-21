"""Multi-Agent tab routes - same shape as the RAG routes.

Browser -> this backend -> shared Multi-Agent server. Every route returns
JSON, and tabs/multi-agent-mode.html prints it.
"""

import os

from flask import Blueprint, request
from services.multi_agent_api import call_multi_agent

multi_agent_mode_bp = Blueprint("multi_agent_mode", __name__)

# Read once at start-up, like MCP_ENABLED and RAG_ENABLED. CI and cloud set it to "false".
MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")


def multi_agent_mode_is_enabled() -> bool:
    if not MULTI_AGENT_ENABLED:
        return False
    header = request.headers.get("X-Multi-Agent-Mode", "on").strip().lower()
    return header in ("1", "true", "yes", "on")


def multi_agent_disabled_response():
    return {"status": "error", "error": "Multi-Agent mode is disabled."}, 403


def to_response(result: dict):
    # The server reports a workflow as completed, degraded or failed; all three
    # are real results the human must see, so only "error" is an HTTP failure.
    if result.get("status") != "error":
        return result, 200
    # 503: the server could not be reached. 502: it answered with an error.
    status = 503 if result.pop("unreachable", False) else 502
    return result, status


@multi_agent_mode_bp.post("/multi-agent/workflow")
def multi_agent_workflow():
    if not multi_agent_mode_is_enabled():
        return multi_agent_disabled_response()

    user_request = request.form.get("user_request", "").strip()
    if not user_request:
        return {"status": "error", "error": "user_request is required"}, 400
    return to_response(call_multi_agent("POST", "/workflow", {"user_request": user_request}))


@multi_agent_mode_bp.get("/multi-agent/workflow/status")
def multi_agent_workflow_status():
    if not multi_agent_mode_is_enabled():
        return multi_agent_disabled_response()
    return to_response(call_multi_agent("GET", "/workflow/status"))


@multi_agent_mode_bp.post("/multi-agent/workflow/<workflow_id>/decision")
def multi_agent_decision(workflow_id):
    if not multi_agent_mode_is_enabled():
        return multi_agent_disabled_response()

    decision = request.form.get("decision", "").strip()
    reason = request.form.get("reason", "").strip()
    if not reason:
        # The server requires a reason for every decision; say so before calling it.
        return {"status": "error", "error": "reason is required"}, 400

    payload = {
        "decision": decision,
        "reason": reason,
        "correction": request.form.get("correction", "").strip(),
        "reviewer": request.form.get("reviewer", "").strip() or "student-5",
    }
    return to_response(call_multi_agent("POST", f"/workflow/{workflow_id}/decision", payload))