"""Client for the shared Multi-Agent server.

The Multi-Agent server runs on the host (not in Docker), so this backend
container reaches it through host.docker.internal, the same way it reaches
Ollama, the MCP server and the RAG server.
"""

import os

import requests

MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://host.docker.internal:5004")

# A workflow runs Planner + Worker, then Reviewer, each calling Ollama, so the
# server can take several minutes. This timeout must be longer than that.
try:
    MULTI_AGENT_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_SERVICE_TIMEOUT_SECONDS", "900"))
except ValueError:
    MULTI_AGENT_TIMEOUT_SECONDS = 900

# Tells the shared server whose data to use. Must match a key in features.py.
FEATURE = "student-5"


def call_multi_agent(method: str, path: str, payload: dict | None = None) -> dict:
    """Call the Multi-Agent server (/workflow, /workflow/status, decision).

    Never raises. A failure comes back as
    {"status": "error", "error": "...", "unreachable": True/False}
    so the route can turn it into a message instead of crashing.
    """
    body = dict(payload or {})
    if path == "/workflow":
        body["feature"] = FEATURE

    try:
        if method == "GET":
            resp = requests.get(f"{MULTI_AGENT_SERVICE_URL}{path}", timeout=MULTI_AGENT_TIMEOUT_SECONDS)
        else:
            resp = requests.post(f"{MULTI_AGENT_SERVICE_URL}{path}", json=body, timeout=MULTI_AGENT_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "unreachable": True,
            "error": f"Multi-Agent server is not reachable at {MULTI_AGENT_SERVICE_URL}. "
                     "Is multi-agent-server/app.py running?",
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "unreachable": True,
            "error": f"Multi-Agent server did not answer within {MULTI_AGENT_TIMEOUT_SECONDS} seconds.",
        }
    except requests.exceptions.RequestException as exc:
        return {"status": "error", "unreachable": True, "error": str(exc)}

    try:
        data = resp.json()
    except ValueError:
        return {"status": "error", "error": f"Multi-Agent server sent a non-JSON reply (HTTP {resp.status_code})."}

    if not isinstance(data, dict):
        return {"status": "error", "error": "Multi-Agent server sent an unexpected reply."}
    if resp.status_code >= 400 and data.get("status") != "error":
        return {"status": "error", "error": f"Multi-Agent server returned HTTP {resp.status_code}."}
    return data