"""Lab 11 JWT token auth — same shape as student-1's routes/auth_mode.py.

POST /auth/token issues a short-lived HS256 token; GET /auth/verify checks a
"Bearer <token>" header. tests/post_commit/test_token_auth.py exercises both.
"""

import os
import time

import jwt
from flask import Blueprint, jsonify, request

auth_bp = Blueprint("auth_mode", __name__)

# Must match tests/post_commit/test_token_auth.py; >= 32 bytes avoids PyJWT's InsecureKeyLengthWarning.
JWT_SECRET = os.getenv("JWT_SECRET", "s2-test-secret-padded-to-32-bytes!!")
TOKEN_LIFETIME_SECONDS = 300  # 5 minute expiry


@auth_bp.post("/auth/token")
def issue_token():
    token = jwt.encode(
        {"sub": "test-user", "exp": time.time() + TOKEN_LIFETIME_SECONDS},
        JWT_SECRET,
        algorithm="HS256",
    )
    return jsonify({"token": token}), 200


@auth_bp.get("/auth/verify")
def verify_token():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        return jsonify({"error": str(exc)}), 401  # expired or invalid signature
    return jsonify({"sub": decoded["sub"]}), 200
