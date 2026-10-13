import os

import requests
from flask import Blueprint, request
from services.multi_agent_api import call_multi_agent_service

multi_agent_mode_bp = Blueprint("multi_agent_mode", __name__)

MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://host.docker.internal:5004")

try:
    MULTI_AGENT_SERVICE_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_SERVICE_TIMEOUT_SECONDS", "60"))
except ValueError:
    MULTI_AGENT_SERVICE_TIMEOUT_SECONDS = 60


def multi_agent_mode_is_enabled(req) -> bool:
    enabled = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
    if not enabled:
        return False

    mode_header = req.headers.get("X-Multi-Agent-Mode", "on").strip().lower()
    return mode_header in ("1", "true", "yes", "on")


def multi_agent_disabled_response():
    return {"status": "error", "error": "Multi-Agent mode is disabled."}, 403



@multi_agent_mode_bp.post("/multi-agent/workflow")
def multi_agent_workflow():
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    data = request.get_json(silent=True) or {}
    user_request = data.get("user_request", "").strip()

    # if not user_request:
    #     return {"status": "error", "error": "user_request is required, multi_agent_mode.py"}, 400

    # try:
    #     response = requests.post(
    #         f"{MULTI_AGENT_SERVICE_URL}/workflow",
    #         json={"user_request": user_request},
    #         timeout=MULTI_AGENT_SERVICE_TIMEOUT_SECONDS,
    #     )
    #     return response.json(), response.status_code
    
    # except requests.RequestException as exc:
    #     return {"status": "error", "error": str(exc)}, 503
    

    # user_request = request.form.get("user_request", "student").strip() or "student"
    try:
        payload = call_multi_agent_service("/workflow", {"user_request": user_request})
        return payload, 200
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc)}, 503


@multi_agent_mode_bp.get("/multi-agent/workflow/status")
def multi_agent_workflow_status():
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    try:
        response = requests.get(
            f"{MULTI_AGENT_SERVICE_URL}/workflow/status",
            timeout=MULTI_AGENT_SERVICE_TIMEOUT_SECONDS,
        )
        return response.json(), response.status_code
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc)}, 503