"""Lab 11 post-commit API tests for the Bank Account database microservice.

Run after `docker compose up -d --build` (database published on host port 8302).
Unlike tests/test_backend_e2e.py these do not skip when the service is down:
an unreachable service is a failed post-commit check.
"""

import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:8302")


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_accounts_exist():
    response = requests.get(f"{DATABASE_SERVICE_URL}/accounts", timeout=5)
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) > 0


def test_account_by_id():
    response = requests.get(f"{DATABASE_SERVICE_URL}/accounts/1", timeout=5)
    assert response.status_code == 200
    assert response.json()["account_id"] == 1


def test_unknown_account_returns_404():
    response = requests.get(f"{DATABASE_SERVICE_URL}/accounts/999999", timeout=5)
    assert response.status_code == 404


def test_accounts_by_user():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/accounts/by-user",
        params={"user_id": 1},
        timeout=5,
    )
    assert response.status_code == 200
    assert all(account["user_id"] == 1 for account in response.json())


def test_accounts_by_status():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/accounts/by-status",
        params={"status": "ACTIVE"},
        timeout=5,
    )
    assert response.status_code == 200
    assert all(account["account_status"] == "ACTIVE" for account in response.json())


def test_account_balance():
    response = requests.get(f"{DATABASE_SERVICE_URL}/accounts/1/balance", timeout=5)
    assert response.status_code == 200
    assert "balance" in response.json()
