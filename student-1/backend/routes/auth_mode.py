import os
import time

import jwt
from flask import Blueprint, jsonify, request


auth_bp = Blueprint("auth_mode", __name__)

JWT_SECRET = os.getenv("JWT_SECRET", "lab11-test-secret-padded-to-32-bytes!!")  # must match test_token_auth.py; >=32 bytes avoids PyJWT's InsecureKeyLengthWarning


@auth_bp.post("/auth/token")
def issue_token():
    token = jwt.encode(
        {"sub": "test-user", "exp": time.time() + 300},  # 5 minute expiry
        JWT_SECRET,
        algorithm="HS256",
    )
    return jsonify({"token": token}), 200


@auth_bp.get("/auth/verify")
def verify_token():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()  # strip "Bearer " prefix
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        return jsonify({"error": str(exc)}), 401  # expired or invalid signature
    return jsonify({"sub": decoded["sub"]}), 200