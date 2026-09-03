"""Unit tests for the account-database microservice.

Runs entirely against a temporary SQLite file (no network, no Docker),
so it can be used as pre-testing evidence before deploying the service.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"
sys.path.insert(0, str(DATABASE_DIR))


@pytest.fixture()
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DB_PATH"] = db_path

    # Reload modules so they pick up the temporary DB_PATH.
    for module_name in ("init_db", "app"):
        sys.modules.pop(module_name, None)

    import init_db as init_db_module

    init_db_module.init_db()

    import app as app_module

    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as test_client:
        yield test_client

    os.remove(db_path)


def test_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "running"


def test_seed_data_has_at_least_ten_accounts(client):
    response = client.get("/accounts")
    accounts = response.get_json()
    assert response.status_code == 200
    assert len(accounts) >= 10


def test_get_account_by_id(client):
    response = client.get("/accounts/1")
    assert response.status_code == 200
    account = response.get_json()
    assert account["account_id"] == 1
    assert account["account_status"] in ("ACTIVE", "FROZEN", "CLOSED")


def test_get_account_not_found(client):
    response = client.get("/accounts/9999")
    assert response.status_code == 404


def test_create_account(client):
    response = client.post(
        "/accounts",
        json={
            "user_id": 42,
            "account_number": "99999999",
            "account_type": "EVERYDAY",
            "balance": 100.0,
        },
    )
    assert response.status_code == 201
    account = response.get_json()
    assert account["account_status"] == "ACTIVE"
    assert account["balance"] == 100.0


def test_create_account_rejects_duplicate_account_number(client):
    payload = {
        "user_id": 1,
        "account_number": "10000001",  # already used by seed data
        "account_type": "EVERYDAY",
        "balance": 0,
    }
    response = client.post("/accounts", json=payload)
    assert response.status_code == 409


def test_create_account_rejects_invalid_type(client):
    response = client.post(
        "/accounts",
        json={"user_id": 1, "account_number": "12345678", "account_type": "BUSINESS"},
    )
    assert response.status_code == 400


def test_create_account_rejects_non_8_digit_number(client):
    for bad_number in ("2", "123", "123456789", "1234567a"):
        response = client.post(
            "/accounts",
            json={"user_id": 1, "account_number": bad_number, "account_type": "EVERYDAY"},
        )
        assert response.status_code == 400, f"expected 400 for {bad_number!r}"


def test_update_account_information(client):
    response = client.put("/accounts/1", json={"account_type": "SAVINGS"})
    assert response.status_code == 200
    assert response.get_json()["account_type"] == "SAVINGS"


def test_update_account_rejects_non_8_digit_number(client):
    response = client.put("/accounts/1", json={"account_number": "2"})
    assert response.status_code == 400


def test_update_account_rejects_existing_account_number(client):
    # account 2's number ("10000002") must not be assignable to account 1 --
    # the unique constraint should block it rather than overwriting account 2.
    response = client.put("/accounts/1", json={"account_number": "10000002"})
    assert response.status_code == 409

    unchanged = client.get("/accounts/1").get_json()
    assert unchanged["account_number"] == "10000001"


def test_adjust_balance_deposit_and_withdraw(client):
    deposit = client.patch("/accounts/1/balance", json={"delta": 50})
    assert deposit.status_code == 200
    balance_after_deposit = deposit.get_json()["balance"]

    withdraw = client.patch("/accounts/1/balance", json={"delta": -20})
    assert withdraw.status_code == 200
    assert withdraw.get_json()["balance"] == pytest.approx(balance_after_deposit - 20)


def test_adjust_balance_rejects_overdraw(client):
    response = client.patch("/accounts/1/balance", json={"delta": -1000000})
    assert response.status_code == 400


def test_freeze_then_balance_change_is_rejected(client):
    freeze = client.post("/accounts/1/freeze")
    assert freeze.status_code == 200
    assert freeze.get_json()["account_status"] == "FROZEN"

    blocked = client.patch("/accounts/1/balance", json={"delta": 10})
    assert blocked.status_code == 409


def test_freeze_twice_is_rejected(client):
    client.post("/accounts/1/freeze")
    second_freeze = client.post("/accounts/1/freeze")
    assert second_freeze.status_code == 409


def test_close_account_then_freeze_is_rejected(client):
    close = client.post("/accounts/1/close")
    assert close.status_code == 200
    assert close.get_json()["account_status"] == "CLOSED"

    freeze_after_close = client.post("/accounts/1/freeze")
    assert freeze_after_close.status_code == 409


def test_delete_account(client):
    response = client.delete("/accounts/1")
    assert response.status_code == 200
    assert client.get("/accounts/1").status_code == 404
