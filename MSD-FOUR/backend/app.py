from flask import Flask, render_template, request
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="../templates")

DATABASE_NAME = Path(__file__).parent.parent / "database" / "users.db"


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

    password_hash = generate_password_hash(password)

    conn = get_db_connection()

    try:
        conn.execute("""
            INSERT INTO users
            (username, email, password_hash, first_name, last_name, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            email,
            password_hash,
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

    if not check_password_hash(user["password_hash"], password):
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


if __name__ == "__main__":
    app.run(debug=True)