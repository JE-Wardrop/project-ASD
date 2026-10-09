import os

import requests

MULTI_AGENT_SERVER_URL = os.getenv("MULTI_AGENT_SERVER_URL", "http://host.docker.internal:5004")
MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")

try:
    MULTI_AGENT_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "180"))
except ValueError:
    MULTI_AGENT_TIMEOUT_SECONDS = 180


def multi_agent_mode_is_enabled(req) -> bool:
    if not MULTI_AGENT_ENABLED:
        return False

    mode_header = req.headers.get("X-MULTI-AGENT-Mode", "on").strip().lower()
    return mode_header in ("1", "true", "yes", "on")


def multi_agent_disabled_response():
    return {"status": "error", "error": "Multi-agent mode is disabled."}, 403


def call_multi_agent_service(path: str, payload: dict):
    response = requests.post(
        f"{MULTI_AGENT_SERVER_URL}{path}",
        json=payload,
        timeout=MULTI_AGENT_TIMEOUT_SECONDS,
    )

    try:
        data = response.json()
    except ValueError:
        response.raise_for_status()
        return {}

    if response.status_code >= 400:
        raise requests.HTTPError(
            f"Multi-agent service {path} failed with status {response.status_code}: {data}",
            response=response,
        )

    return data