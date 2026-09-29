from flask import Blueprint, request
import requests

from services.rag_api import call_rag_service, rag_disabled_response, rag_mode_is_enabled


rag_mode_bp = Blueprint("rag_mode", __name__)


@rag_mode_bp.post("/rag/refresh")
def rag_refresh():
    if not rag_mode_is_enabled(request):
        return rag_disabled_response()

    caller = request.form.get("caller", "student").strip() or "student"
    try:
        payload = call_rag_service("/refresh", {"caller": caller})
        return payload, 200
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc)}, 503


@rag_mode_bp.post("/rag/answer")
def rag_answer():
    if not rag_mode_is_enabled(request):
        return rag_disabled_response()

    query = request.form.get("query", "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}, 400
    
    k = int(request.form.get("k", "5"))

    try:
        # Original Code
        payload = call_rag_service("/answer", {"query": query, "k": k, "caller": "student"})

        # I think that "student" should be for user or something
        # In rag_eval it was mentioned that k precision was different due to the k factor being
        # removed, so I am not sending it to the JSON payload anymore.

        # payload = call_rag_service("/answer", {"query": query, "caller": "student"})


        return payload, 200
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc)}, 503

    

@rag_mode_bp.post("/rag/retrieve")
def rag_retrieve():
    if not rag_mode_is_enabled(request):
        return rag_disabled_response()

    caller = request.form.get("caller", "student").strip() or "student"
    try:
        payload = call_rag_service("/retrieve", {"caller": caller})
        return payload, 200
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc)}, 503