from flask import Flask, jsonify, request
import sqlite3
from pathlib import Path
from flask_cors import CORS
    

app = Flask(__name__)

DATABASE_NAME = Path(__file__).parent / "users.db"
# CORS(app)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def health():
    return jsonify({"service": "database-service", "status": "running"})


@app.get("/users")
def get_users():
    conn = get_db_connection()
    users = conn.execute(
        "SELECT user_id, username, email, role, first_name, last_name, phone FROM users"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in users])


@app.get("/users/<int:user_id>")
def get_user(user_id):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT user_id, username, email, first_name, last_name, phone FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user))


@app.get("/users/by-username")
def get_user_by_username():
    # Returns password_hash too - internal/server-to-server use only,
    # so user-service can verify logins without opening the SQLite file.
    username = request.args.get("username", "").strip()

    if not username:
        return jsonify({"error": "username required"}), 400

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user))


@app.post("/users")
def create_user():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    first_name = (data.get("fname") or "").strip()
    last_name = (data.get("lname") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = (data.get("role") or "").strip()

    if not username or not email or not password:
        return jsonify({"error": "username, email and password are required"}), 400

    conn = get_db_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO users (username, email, password, first_name, last_name, phone, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, email, password, first_name, last_name, phone, role),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Username or email already exists"}), 409

    conn.close()
    return jsonify({"user_id": new_id, "message": "User created"}), 201


@app.put("/users/<int:user_id>")
def update_user(user_id):
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip()
    first_name = (data.get("fname") or "").strip()
    last_name = (data.get("lname") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = (data.get("role") or "").strip()

    if not email or not first_name or not last_name or not phone:
        return jsonify({"error": "email, first_name, last_name and phone are required"}), 400

    conn = get_db_connection()

    existing = conn.execute(
        "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    conn.execute(
        """
        UPDATE users
        SET email = ?, first_name = ?, last_name = ?, phone = ?, role = ?, 
        WHERE user_id = ?
        """,
        (email, first_name, last_name, phone, role, user_id),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "User updated"})


@app.delete("/users/<int:user_id>")
def delete_user(user_id):
    conn = get_db_connection()

    existing = conn.execute(
        "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "User deleted"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
