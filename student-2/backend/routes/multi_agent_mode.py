"""Multi-Agent tab routes — same endpoints as student-1's routes/multi_agent_mode.py.

Browser -> this backend -> shared Multi-Agent Server
(Planner + Worker -> Reviewer -> Human Review). Every route returns JSON, and
tabs/multi-agent.html renders it. A workflow comes back with its human
decision "pending"; the decision route records the final call on the server.

    POST /multi-agent/workflow          {"user_request": "..."}
    POST /multi-agent/workflow/<id>/decision {"decision", "reason", "correction"}
    GET  /multi-agent/workflow/status
"""

import os

from flask import Blueprint, request

from services.multi_agent_api import record_decision, run_workflow, workflow_status

multi_agent_mode_bp = Blueprint("multi_agent_mode", __name__)

# Read once at start-up, like RAG_ENABLED. CI and the cloud deployment set it to "false".
MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")


def multi_agent_mode_is_enabled(req) -> bool:
    if not MULTI_AGENT_ENABLED:
        return False

    mode_header = req.headers.get("X-Multi-Agent-Mode", "on").strip().lower()
    return mode_header in ("1", "true", "yes", "on")


def multi_agent_disabled_response():
    return {"status": "error", "error": "Multi-Agent mode is disabled."}, 403


def to_response(result: dict):
    http_status = result.pop("http_status", None)
    if result.get("status") != "error":
        return result, 200
    # 503: the Multi-Agent Server could not be reached.
    if result.pop("unreachable", False):
        return result, 503
    # 4xx: the server rejected the input. Anything else: it failed, so 502.
    if http_status and 400 <= http_status < 500:
        return result, http_status
    return result, 502


@multi_agent_mode_bp.post("/multi-agent/workflow")
def multi_agent_workflow():
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    data = request.get_json(silent=True) or {}
    user_request = str(data.get("user_request", "")).strip()

    if not user_request:
        return {"status": "error", "error": "user_request is required"}, 400

    return to_response(run_workflow(user_request))


@multi_agent_mode_bp.post("/multi-agent/workflow/<workflow_id>/decision")
def multi_agent_decision(workflow_id):
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    data = request.get_json(silent=True) or {}
    decision = str(data.get("decision", "")).strip()
    reason = str(data.get("reason", "")).strip()
    correction = str(data.get("correction", "")).strip()

    # The server enforces these too; checking here gives a clearer message first.
    if not decision or not reason:
        return {"status": "error", "error": "decision and reason are required"}, 400
    if decision == "Partially Accept" and not correction:
        return {"status": "error", "error": "correction is required for Partially Accept"}, 400

    return to_response(record_decision(
        workflow_id, decision, reason, correction,
        str(data.get("reviewer", "student-2")).strip() or "student-2",
    ))


@multi_agent_mode_bp.get("/multi-agent/workflow/status")
def multi_agent_workflow_status():
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    return to_response(workflow_status())
