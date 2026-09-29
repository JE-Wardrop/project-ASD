"""RAG tab routes — same shape as Lab 8's routes/rag_mode.py.

Browser -> this backend -> shared RAG server. Every route returns JSON, and
tabs/rag.html prints it.
"""

import os

from flask import Blueprint, request

from services.rag_api import call_rag

rag_mode_bp = Blueprint("rag_mode", __name__)

# Read once at start-up, like MCP_ENABLED. CI sets it to "false".
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")

MAX_K = 20


def rag_mode_is_enabled() -> bool:
    # Two switches, like Lab 8: the environment variable (CI turns it off)
    # and the X-RAG-Mode header that the tab's toggle sends.
    if not RAG_ENABLED:
        return False
    header = request.headers.get("X-RAG-Mode", "on").strip().lower()
    return header in ("1", "true", "yes", "on")


def rag_disabled_response():
    return {"status": "error", "error": "RAG mode is disabled."}, 403


def read_k() -> int:
    try:
        k = int(request.form.get("k", "5"))
    except ValueError:
        k = 5
    return max(1, min(k, MAX_K))


def to_response(result: dict):
    if result.get("status") == "success":
        return result, 200
    # 503: the RAG server could not be reached. 502: it answered with an error.
    status = 503 if result.pop("unreachable", False) else 502
    return result, status


@rag_mode_bp.post("/rag/refresh")
def rag_refresh():
    if not rag_mode_is_enabled():
        return rag_disabled_response()
    return to_response(call_rag("/refresh"))


@rag_mode_bp.post("/rag/retrieve")
def rag_retrieve():
    if not rag_mode_is_enabled():
        return rag_disabled_response()

    query = request.form.get("query", "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}, 400
    return to_response(call_rag("/retrieve", {"query": query, "k": read_k()}))


@rag_mode_bp.post("/rag/answer")
def rag_answer():
    if not rag_mode_is_enabled():
        return rag_disabled_response()

    query = request.form.get("query", "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}, 400
    return to_response(call_rag("/answer", {"query": query, "k": read_k()}))