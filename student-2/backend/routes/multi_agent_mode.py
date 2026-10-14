"""Multi-Agent tab routes — same shape as routes/rag_mode.py.

Browser -> this backend -> shared Multi-Agent Server
(Planner + Worker -> Reviewer -> Human decision). Every route returns JSON,
and tabs/multi-agent.html renders it.
"""

import os

from flask import Blueprint, request

from services.multi_agent_api import record_decision, run_workflow, workflow_status

multi_agent_mode_bp = Blueprint("multi_agent_mode", __name__)

# Read once at start-up, like RAG_ENABLED. CI sets it to "false".
MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")


def multi_agent_mode_is_enabled() -> bool:
    if not MULTI_AGENT_ENABLED:
        return False
    header = request.headers.get("X-Multi-Agent-Mode", "on").strip().lower()
    return header in ("1", "true", "yes", "on")


def multi_agent_disabled_response():
    return {"status": "error", "error": "Multi-Agent mode is disabled."}, 403


def to_response(result: dict):
    http_status = result.pop("http_status", None)
    if result.get("status") != "error":
        return result, 200
    # 503: the Multi-Agent Server could not be reached.
    if result.pop("unreachable", False):
        return result, 503
    # 4xx: the server rejected the input (bad decision, unknown workflow,
    # decision already recorded). Anything else: it failed, so 502.
    if http_status and 400 <= http_status < 500:
        return result, http_status
    return result, 502


@multi_agent_mode_bp.post("/multi-agent/workflow")
def multi_agent_workflow():
    if not multi_agent_mode_is_enabled():
        return multi_agent_disabled_response()

    user_request = request.form.get("user_request", "").strip()
    if not user_request:
        return {"status": "error", "error": "user_request is required"}, 400
    return to_response(run_workflow(user_request))


@multi_agent_mode_bp.post("/multi-agent/decision")
def multi_agent_decision():
    if not multi_agent_mode_is_enabled():
        return multi_agent_disabled_response()

    workflow_id = request.form.get("workflow_id", "").strip()
    if not workflow_id:
        return {"status": "error", "error": "workflow_id is required"}, 400

    return to_response(record_decision(
        workflow_id,
        request.form.get("decision", "").strip(),
        request.form.get("reason", "").strip(),
        request.form.get("correction", "").strip(),
        request.form.get("reviewer", "").strip() or "student-2",
    ))


@multi_agent_mode_bp.get("/multi-agent/status")
def multi_agent_status():
    if not multi_agent_mode_is_enabled():
        return multi_agent_disabled_response()
    return to_response(workflow_status())
