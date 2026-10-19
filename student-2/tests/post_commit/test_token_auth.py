"""Lab 11 post-commit token tests.

The first three tests check PyJWT behaviour directly (no services needed).
The last two call student-2's own /auth/token and /auth/verify routes
(backend published on host port 8202), so the real auth code is tested too.
"""

import os
import time

import jwt
import pytest
import requests

JWT_SECRET = os.getenv("JWT_SECRET", "s2-test-secret-padded-to-32-bytes!!")
BACKEND_SERVICE_URL = os.getenv("BACKEND_SERVICE_URL", "http://localhost:8202")
# Deliberately wrong test-only key; >= 32 bytes avoids InsecureKeyLengthWarning.
WRONG_SECRET = "wrong-secret-also-padded-to-32-bytes!!"  # noqa: S105 - not a real credential


def make_token(exp_offset_seconds):
    return jwt.encode(
        {"sub": "test-user", "exp": time.time() + exp_offset_seconds},
        JWT_SECRET,
        algorithm="HS256",
    )


def test_valid_token_decodes():
    token = make_token(60)
    decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    assert decoded["sub"] == "test-user"


def test_expired_token_rejected():
    token = make_token(-60)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


def test_invalid_signature_rejected():
    token = make_token(60)
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, WRONG_SECRET, algorithms=["HS256"])


def test_backend_issues_and_verifies_token():
    issued = requests.post(f"{BACKEND_SERVICE_URL}/auth/token", timeout=5)
    assert issued.status_code == 200
    token = issued.json()["token"]

    verified = requests.get(
        f"{BACKEND_SERVICE_URL}/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert verified.status_code == 200
    assert verified.json()["sub"] == "test-user"


def test_backend_rejects_expired_token():
    response = requests.get(
        f"{BACKEND_SERVICE_URL}/auth/verify",
        headers={"Authorization": f"Bearer {make_token(-60)}"},
        timeout=5,
    )
    assert response.status_code == 401
