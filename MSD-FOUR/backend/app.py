from flask import Flask, render_template, request
import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="../templates")

DATABASE_NAME = Path(__file__).parent.parent / "database" / "users.db"


# =========================
# AI-Mode configuration (Ollama via the OpenAI-compatible API)
# =========================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

def load_prompt(filename):
    prompt_path = PROMPT_DIR / filename
    return prompt_path.read_text(encoding="utf-8").strip()


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# Front end right on startup
# =========================
@app.route("/")
def index():
    return render_template("frontend.html")
# =========================
# GET ALL USERS
# =========================

@app.route("/users", methods=["GET"])
def get_users():
    conn = get_db_connection()

    users = conn.execute("""
        SELECT user_id, username, email, first_name, last_name, phone
        FROM users
    """).fetchall()

    conn.close()

    html = "<ul>"

    for user in users:
        html += (
            f"<li>"
            f"{user['user_id']} - "
            f"{user['username']} - "
            f"{user['email']} - "
            f"{user['first_name']} {user['last_name']}"
            f"</li>"
        )

    html += "</ul>"

    return html


# =========================
# GET ONE USER
# =========================

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_db_connection()

    user = conn.execute("""
        SELECT user_id, username, email, first_name, last_name, phone
        FROM users
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    conn.close()

    if user is None:
        return "<p>User not found.</p>", 404

    return (
        f"<p>"
        f"ID: {user['user_id']}<br>"
        f"Username: {user['username']}<br>"
        f"Email: {user['email']}<br>"
        f"Name: {user['first_name']} {user['last_name']}<br>"
        f"Phone: {user['phone']}"
        f"</p>"
    )


# =========================
# REGISTER USER
# =========================

@app.route("/users/register", methods=["POST"])
def register_user():

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not username or not email or not password:
        return "<p>Username, email and password are required.</p>", 400

    # password_hash = generate_password_hash(password)

    conn = get_db_connection()

    try:
        conn.execute("""
            INSERT INTO users
            (username, email, password, first_name, last_name, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            email,
            password,
            first_name,
            last_name,
            phone
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return "<p>Username or email already exists.</p>", 409

    conn.close()

    return "<p>User registered successfully.</p>", 201


# =========================
# LOGIN
# =========================

@app.route("/users/login", methods=["POST"])
def login_user():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return "<p>Username and password are required.</p>", 400

    conn = get_db_connection()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE username = ?
    """, (username,)).fetchone()

    conn.close()

    if user is None:
        return "<p>Invalid username or password.</p>", 401

    if user["password"] != password:
        return "<p>Invalid username or password.</p>", 401

    return (
        f"<p>"
        f"Login successful.<br>"
        f"Welcome, {user['first_name']}!"
        f"</p>"
    )


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
        return "<p>All fields are required.</p>", 400

    conn = get_db_connection()

    existing_user = conn.execute("""
        SELECT user_id
        FROM users
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    if existing_user is None:
        conn.close()
        return "<p>User not found.</p>", 404

    conn.execute("""
        UPDATE users
        SET email = ?,
            first_name = ?,
            last_name = ?,
            phone = ?
        WHERE user_id = ?
    """, (
        email,
        first_name,
        last_name,
        phone,
        user_id
    ))

    conn.commit()
    conn.close()

    return "<p>User updated successfully.</p>"


# =========================
# DELETE USER
# =========================

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):

    conn = get_db_connection()

    existing_user = conn.execute("""
        SELECT user_id
        FROM users
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    if existing_user is None:
        conn.close()
        return "<p>User not found.</p>", 404

    conn.execute("""
        DELETE FROM users
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    return "<p>User deleted successfully.</p>"

# =========================
# AI HELP (Ollama, OpenAI-compatible API)
# =========================

@app.route("/users/help", methods=["POST"])
def ask_user_help():

    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    system_prompt = load_prompt("user_management_sys_prompt.txt")
    task_prompt = load_prompt("user_help_task_prompt.txt")

    final_prompt = f"{task_prompt}\n\nUser question: {question}"

    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt}
            ],
            max_tokens=300,
            temperature=0.2,
        )

        answer = response.choices[0].message.content

        return f"<p>{answer}</p>"

    except Exception as exc:
        return (
            "<p>Local AI agent request failed. "
            f"Check that Ollama is running and that {OLLAMA_MODEL} is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )



if __name__ == "__main__":
    app.run(debug=True)