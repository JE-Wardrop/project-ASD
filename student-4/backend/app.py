from flask import Flask, render_template, request, jsonify
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from flask_cors import CORS
import requests


app = Flask(__name__, template_folder="../frontend/templates")
CORS(app)


# =========================
# Database Service
# =========================

DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL",
    "http://localhost:5002"
)


# =========================
# AI-Mode configuration
# Ollama via OpenAI-compatible API
# =========================

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434/v1"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b"
)

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(filename):
    prompt_path = PROMPT_DIR / filename
    return prompt_path.read_text(encoding="utf-8").strip()


# =========================
# Frontend
# =========================

@app.route("/")
def index():
    return render_template("frontend.html")


# =========================
# GET ALL USERS
# =========================

@app.route("/users", methods=["GET"])
def get_users():

    try:
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/users",
            timeout=5
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(exc)
        }), 503

    if response.status_code != 200:
        return jsonify({
            "error": "Database service error"
        }), 502

    return jsonify(response.json())


# =========================
# GET ONE USER
# =========================

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):

    try:
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/users/{user_id}",
            timeout=5
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(exc)
        }), 503

    if response.status_code == 404:
        return jsonify({
            "error": "User not found"
        }), 404

    if response.status_code != 200:
        return jsonify({
            "error": "Database service error"
        }), 502

    return jsonify(response.json())


# =========================
# REGISTER USER
# =========================

@app.route("/users", methods=["POST"])
def register_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    first_name = (data.get("fname") or "").strip()
    last_name = (data.get("lname") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = (data.get("role") or "").strip()

    if not username or not email or not password:
        return jsonify({
            "error": "Username, email and password are required"
        }), 400

    data = {
        "username": username,
        "email": email,
        "password": password,
        "fname": first_name,
        "lname": last_name,
        "phone": phone,
        "role": role
    }

    try:
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/users",
            json=data,
            timeout=5
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(exc)
        }), 503

    if response.status_code == 409:
        return jsonify(response.json()), 409

    if response.status_code != 201:
        return jsonify({
            "error": "Database service error"
        }), 502

    return jsonify(response.json()), 201


# =========================
# LOGIN
# =========================

@app.route("/users/login", methods=["POST"])
def login_user():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return jsonify({
            "error": "Username and password are required"
        }), 400

    try:
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/users/by-username",
            params={
                "username": username
            },
            timeout=5
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(exc)
        }), 503

    if response.status_code == 404:
        return jsonify({
            "error": "Invalid username or password"
        }), 401

    if response.status_code != 200:
        return jsonify({
            "error": "Database service error"
        }), 502

    user = response.json()

    # Plain-text password comparison.
    # No hashing.
    if user["password"] != password:
        return jsonify({
            "error": "Invalid username or password"
        }), 401

    return jsonify({
        "message": "Login successful",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "phone": user["phone"]
        }
    }), 200


# =========================
# UPDATE USER
# =========================

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):

    email = request.form.get("email", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not email or not first_name or not last_name or not phone:
        return jsonify({
            "error": "All fields are required"
        }), 400

    data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone
    }

    try:
        response = requests.put(
            f"{DATABASE_SERVICE_URL}/users/{user_id}",
            json=data,
            timeout=5
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(exc)
        }), 503

    if response.status_code == 404:
        return jsonify({
            "error": "User not found"
        }), 404

    if response.status_code != 200:
        return jsonify({
            "error": "Database service error"
        }), 502

    return jsonify(response.json()), 200


# =========================
# DELETE USER
# =========================

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):

    try:
        response = requests.delete(
            f"{DATABASE_SERVICE_URL}/users/{user_id}",
            timeout=5
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Database service unavailable",
            "details": str(exc)
        }), 503

    if response.status_code == 404:
        return jsonify({
            "error": "User not found"
        }), 404

    if response.status_code != 200:
        return jsonify({
            "error": "Database service error"
        }), 502

    return jsonify(response.json()), 200


# =========================
# AI HELP
# Ollama, OpenAI-compatible API
# =========================

@app.route("/users/help", methods=["POST"])
def ask_user_help():

    question = request.form.get("question", "").strip()

    print("DEBUG question:", repr(question))

    if not question:
        return jsonify({
            "error": "Question is required"
        }), 400

    system_prompt = load_prompt(
        "user_management_sys_prompt.txt"
    )

    task_prompt = load_prompt(
        "user_help_task_prompt.txt"
    )

    final_prompt = (
        f"{task_prompt}\n\n"
        f"User question: {question}"
    )

    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],
            max_tokens=300,
            temperature=0.2
        )

        answer = response.choices[0].message.content
        return jsonify({
            "response": answer
        })

    except Exception as exc:

        print("AI ERROR:", exc)

        return jsonify({
            "error": "Local AI agent request failed.",
            "details": str(exc)
        }), 503


# =========================
# Start application
# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )