"""Client for the shared RAG server (same contract as student-5's rag_api.py).

The RAG server runs on the host (not in Docker), so this backend container
reaches it through host.docker.internal, the same way it reaches Ollama and
the MCP server.
"""

import os

import requests

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://host.docker.internal:5003")

# The RAG server can wait up to 120 s for Ollama to write an answer, so this
# timeout must be longer than that, or this backend gives up first.
try:
    RAG_TIMEOUT_SECONDS = int(os.getenv("RAG_SERVICE_TIMEOUT_SECONDS", "180"))
except ValueError:
    RAG_TIMEOUT_SECONDS = 180

CALLER = "student-2"

# Limits every search to Bank Account Management's own records and rules
# (accounts database rows + knowledge/accounts.md).
FEATURE = "accounts"


def call_rag(path: str, payload: dict | None = None) -> dict:
    """POST to the RAG server (/refresh, /retrieve or /answer).

    Never raises. A failure comes back as
    {"status": "error", "error": "...", "unreachable": True/False}
    so the route can turn it into a message instead of crashing.
    """
    body = {"caller": CALLER, **(payload or {})}
    if path in ("/retrieve", "/answer"):
        body["feature"] = FEATURE

    try:
        resp = requests.post(f"{RAG_SERVICE_URL}{path}", json=body, timeout=RAG_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "unreachable": True,
            "error": f"RAG server is not reachable at {RAG_SERVICE_URL}. "
                     "Is rag_http_server.py running?",
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "unreachable": True,
            "error": f"RAG server did not answer within {RAG_TIMEOUT_SECONDS} seconds.",
        }
    except requests.exceptions.RequestException as exc:
        return {"status": "error", "unreachable": True, "error": str(exc)}

    try:
        data = resp.json()
    except ValueError:
        return {"status": "error", "error": f"RAG server sent a non-JSON reply (HTTP {resp.status_code})."}

    if not isinstance(data, dict):
        return {"status": "error", "error": "RAG server sent an unexpected reply."}
    if resp.status_code >= 400 and data.get("status") != "error":
        return {"status": "error", "error": f"RAG server returned HTTP {resp.status_code}."}
    return data
