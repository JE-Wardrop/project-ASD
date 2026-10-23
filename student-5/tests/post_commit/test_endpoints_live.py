"""Post-commit endpoint tests for student-5 (Transaction Management).

student-5.yml runs these after the containers start. They call the real
backend on port 8205, which calls the real database API, so they test two
deployed endpoint functions end to end instead of mocks:

  1. list_transactions  -> GET /transactions
  2. get_transaction    -> GET /transactions/<txn_id>
"""

import os

import pytest
import requests

BACKEND_URL = os.getenv("STUDENT5_BACKEND_URL", "http://localhost:8205")
TIMEOUT = 10


def _get(path: str) -> requests.Response:
    try:
        return requests.get(f"{BACKEND_URL}{path}", timeout=TIMEOUT)
    except requests.RequestException as exc:
        pytest.fail(f"Backend not reachable at {BACKEND_URL}{path}: {exc}")


def test_list_transactions_endpoint():
    """GET /transactions returns the seeded rows, honours limit, and has the expected fields."""
    resp = _get("/transactions?limit=5")

    assert resp.status_code == 200
    body = resp.json()
    rows = body.get("transactions")
    assert isinstance(rows, list)
    assert 0 < len(rows) <= 5
    assert body.get("count") == len(rows)
    for field in ("transaction_id", "transaction_type", "amount", "status"):
        assert field in rows[0], f"missing field {field}"


def test_get_transaction_endpoint():
    """GET /transactions/<id> returns that one row, and 404 for an id that does not exist."""
    first_id = _get("/transactions?limit=1").json()["transactions"][0]["transaction_id"]

    found = _get(f"/transactions/{first_id}")
    assert found.status_code == 200
    assert found.json()["transaction_id"] == first_id

    missing = _get("/transactions/999999")
    assert missing.status_code == 404