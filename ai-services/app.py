"""
============================================================
AI-MODE SERVICE - Unified AI service for all students.

Each member's backend calls this service instead of calling Ollama directly, to:
- declare Ollama's address in ONE place
- change the model for the whole group via an environment variable
- share a common request/response format for all users
Flow:
  Frontend -> Backend/API -> ai-service -> Ollama -> LLM

Run in local : PORT=8090 python app.py
Docker     : port 8000 map to host 8090
============================================================
"""

import os
import logging

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI, OpenAIError


OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")

TIMEOUT = float(os.environ.get("AI_TIMEOUT", "120"))

SERVICE_NAME = "ai-service"

app = Flask(__name__)
CORS(app)

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=TIMEOUT,
)

# /health asking model list inside Ollama so we need to remove /v1 from the base url
OLLAMA_ROOT = OLLAMA_BASE_URL.rsplit("/v1", 1)[0]

#  checking ollama running and getting model list
@app.get("/health")
def health():
    try:
        resp = requests.get(f"{OLLAMA_ROOT}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "ollama": "up",
            "models": models,
            "default_model": DEFAULT_MODEL,
        }, 200
    except requests.RequestException as exc:
        return {
            "status": "degraded",
            "service": SERVICE_NAME,
            "ollama": "down",
            "detail": str(exc),
        }, 503


@app.post("/ai/generate")
def generate():
    """Nhan  {"prompt": "...", "model": "..."}  (model khong bat buoc)
    Tra ve  {"response": "...", "model": "..."}

    Day la contract dung chung cho ca nhom - dung doi ten truong."""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()

    if not prompt:
        return {"error": "prompt is required"}, 400

    model = data.get("model") or DEFAULT_MODEL

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,     # thap = tra loi on dinh, it bia
            max_tokens=300,      # chan cau tra loi lan man
        )
    except OpenAIError as exc:
        app.logger.error("Ollama loi: %s", exc)
        return {"error": "AI model is not available", "detail": str(exc)}, 503

    answer = (completion.choices[0].message.content or "").strip()
    return jsonify({"response": answer, "model": model}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
