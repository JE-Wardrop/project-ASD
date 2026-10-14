"""Client for the shared Multi-Agent Server (ai-services/multi-agent-server).

The Multi-Agent Server runs on the host (not in Docker), so this backend
container reaches it through host.docker.internal, the same way it reaches
Ollama, the MCP server and the RAG server.
"""

import os

import requests

MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://host.docker.internal:5004")

# One workflow runs Planner + Worker, then the Reviewer, and each step may wait
# on Ollama (the reviewer can try two models), so allow well over a few minutes.
try:
    MULTI_AGENT_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_SERVICE_TIMEOUT_SECONDS", "300"))
except ValueError:
    MULTI_AGENT_TIMEOUT_SECONDS = 300

CALLER = "student-2"

# Keeps the Worker Agent on Bank Account Management's own database API.
FEATURE = "accounts"


def _request(method: str, path: str, **kwargs) -> dict:
    """Call the Multi-Agent Server.

    Never raises. A failure comes back as
    {"status": "error", "error": "...", "unreachable": True/False}
    so the route can turn it into a message instead of crashing.
    """
    try:
        resp = requests.request(
            method,
            f"{MULTI_AGENT_SERVICE_URL}{path}",
            timeout=MULTI_AGENT_TIMEOUT_SECONDS,
            **kwargs,
        )
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "unreachable": True,
            "error": f"Multi-Agent Server is not reachable at {MULTI_AGENT_SERVICE_URL}. "
                     "Is multi-agent-server/app.py running?",
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "unreachable": True,
            "error": f"Multi-Agent Server did not answer within {MULTI_AGENT_TIMEOUT_SECONDS} seconds.",
        }
    except requests.exceptions.RequestException as exc:
        return {"status": "error", "unreachable": True, "error": str(exc)}

    try:
        data = resp.json()
    except ValueError:
        return {"status": "error", "error": f"Multi-Agent Server sent a non-JSON reply (HTTP {resp.status_code})."}

    if not isinstance(data, dict):
        return {"status": "error", "error": "Multi-Agent Server sent an unexpected reply."}
    if resp.status_code >= 400:
        # Kept so the route can pass 400/404/409 (bad decision input) back to the browser.
        return {
            "status": "error",
            "http_status": resp.status_code,
            "error": data.get("error") or f"Multi-Agent Server returned HTTP {resp.status_code}.",
        }
    return data


def run_workflow(user_request: str) -> dict:
    return _request(
        "POST",
        "/workflow",
        json={"user_request": user_request, "feature": FEATURE, "caller": CALLER},
    )


def record_decision(workflow_id: str, decision: str, reason: str, correction: str, reviewer: str) -> dict:
    return _request(
        "POST",
        f"/workflow/{workflow_id}/decision",
        json={"decision": decision, "reason": reason, "correction": correction, "reviewer": reviewer},
    )


def workflow_status() -> dict:
    return _request("GET", "/workflow/status", params={"feature": FEATURE})
