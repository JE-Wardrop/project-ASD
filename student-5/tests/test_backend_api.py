"""API tests for the backend service routes (routes/normal_ui.py + app.py).

The three downstream services (database, accounts, notifications) are replaced
with mocks so we exercise only this service's own logic: validation, the
deposit / withdraw / transfer flows, passthrough and the HTMX UI endpoints.
"""

from unittest.mock import MagicMock

import pytest

# monkeypatch.setattr(1,2,3)
# 1. The module or object to patch.
# 2. The attribute/function name to patch.
# 3. The new value to set the attribute/function to.
@pytest.fixture
def active_account():
    return {"user_id": 7, "account_status": "ACTIVE", "balance": 1000.0}


# --------------------------------------------------------------------------- #
# /health  &  unknown routes                                                  #
# --------------------------------------------------------------------------- #
def test_health_up_when_database_healthy(client, services, monkeypatch, FakeResp):
    # replace health() with a lambda that returns a FakeResp with status_code 200
    monkeypatch.setattr(services.db, "health", lambda: FakeResp({}, 200))
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["database"] == "up"


def test_health_degraded_when_database_raises(client, services, monkeypatch):
    def boom():
        raise RuntimeError("no db")

    monkeypatch.setattr(services.db, "health", boom)
    resp = client.get("/health")
    assert resp.status_code == 503
    body = resp.get_json()
    assert body["status"] == "degraded"
    assert body["database"] == "down"


def test_unknown_route_returns_custom_404(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Endpoint does not exist"}


# --------------------------------------------------------------------------- #
# READ endpoints - passthrough to the database service                        #
# --------------------------------------------------------------------------- #
def test_list_transactions_passes_through_body_and_status(client, services, monkeypatch, FakeResp):
    payload = {"count": 1, "transactions": [{"transaction_id": 1}]}
    monkeypatch.setattr(services.db, "list_transactions", lambda params: FakeResp(payload, 200))
    resp = client.get("/transactions")
    assert resp.status_code == 200
    assert resp.get_json() == payload


def test_get_transaction_passes_through_404(client, services, monkeypatch, FakeResp):
    monkeypatch.setattr(services.db, "get_transaction", lambda _id: FakeResp({"error": "nope"}, 404))
    resp = client.get("/transactions/5")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "nope"}


def test_account_transactions_injects_account_id_filter(client, services, monkeypatch, FakeResp):
    seen = {}

    def fake_list(params):
        seen.update(params)
        return FakeResp({"transactions": []}, 200)

    monkeypatch.setattr(services.db, "list_transactions", fake_list)
    client.get("/accounts/1001/transactions?status=COMPLETED")
    assert seen == {"status": "COMPLETED", "account_id": 1001}


# --------------------------------------------------------------------------- #
# POST /transactions/deposit                                                  #
# --------------------------------------------------------------------------- #
def test_deposit_happy_path(client, services, monkeypatch, FakeResp, active_account):
    monkeypatch.setattr(services.accounts, "get_account", lambda _id: dict(active_account))
    adjust = MagicMock(return_value=True)
    update = MagicMock()
    notify = MagicMock(return_value=True)
    monkeypatch.setattr(services.accounts, "adjust_balance", adjust)
    monkeypatch.setattr(services.db, "create_transaction",
                        lambda body: FakeResp({"transaction_id": 42, "status": "PENDING"}, 201))
    monkeypatch.setattr(services.db, "update_transaction", update)
    monkeypatch.setattr(services.notify, "send", notify)

    resp = client.post("/transactions/deposit", json={"receiver_account_id": 1001, "amount": 50})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["transaction_id"] == 42
    assert body["status"] == "COMPLETED"
    adjust.assert_called_once_with(1001, 50.0)
    update.assert_called_once_with(42, {"status": "COMPLETED"})
    assert notify.call_args[0][0] == 7                     # notified user_id


def test_deposit_requires_receiver(client):
    resp = client.post("/transactions/deposit", json={"amount": 50})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "receiver_account_id is required"


def test_deposit_rejects_bad_amount(client, services, monkeypatch, active_account):
    monkeypatch.setattr(services.accounts, "get_account", lambda _id: dict(active_account))
    resp = client.post("/transactions/deposit", json={"receiver_account_id": 1001, "amount": -5})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Amount must be greater than 0"


def test_deposit_rejects_frozen_account(client, services, monkeypatch):
    monkeypatch.setattr(services.accounts, "get_account",
                        lambda _id: {"account_status": "FROZEN", "user_id": 7})
    resp = client.post("/transactions/deposit", json={"receiver_account_id": 1001, "amount": 50})
    assert resp.status_code == 400
    assert "FROZEN" in resp.get_json()["error"]


def test_deposit_marks_failed_when_balance_update_fails(client, services, monkeypatch, FakeResp, active_account):
    monkeypatch.setattr(services.accounts, "get_account", lambda _id: dict(active_account))
    monkeypatch.setattr(services.accounts, "adjust_balance", MagicMock(return_value=False))
    monkeypatch.setattr(services.db, "create_transaction",
                        lambda body: FakeResp({"transaction_id": 42, "status": "PENDING"}, 201))
    update = MagicMock()
    notify = MagicMock()
    monkeypatch.setattr(services.db, "update_transaction", update)
    monkeypatch.setattr(services.notify, "send", notify)

    resp = client.post("/transactions/deposit", json={"receiver_account_id": 1001, "amount": 50})

    assert resp.status_code == 502
    assert resp.get_json()["status"] == "FAILED"
    update.assert_called_once_with(42, {"status": "FAILED"})
    notify.assert_not_called()


# --------------------------------------------------------------------------- #
# POST /transactions/withdraw                                                 #
# --------------------------------------------------------------------------- #
def test_withdraw_happy_path_debits_sender(client, services, monkeypatch, FakeResp, active_account):
    monkeypatch.setattr(services.accounts, "get_account", lambda _id: dict(active_account))
    adjust = MagicMock(return_value=True)
    monkeypatch.setattr(services.accounts, "adjust_balance", adjust)
    monkeypatch.setattr(services.db, "create_transaction",
                        lambda body: FakeResp({"transaction_id": 7, "status": "PENDING"}, 201))
    monkeypatch.setattr(services.db, "update_transaction", MagicMock())
    monkeypatch.setattr(services.notify, "send", MagicMock(return_value=True))

    resp = client.post("/transactions/withdraw", json={"sender_account_id": 1001, "amount": 200})

    assert resp.status_code == 201
    assert resp.get_json()["status"] == "COMPLETED"
    adjust.assert_called_once_with(1001, -200.0)           # note: negative delta


def test_withdraw_requires_sender(client):
    resp = client.post("/transactions/withdraw", json={"amount": 10})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "sender_account_id is required"


def test_withdraw_rejects_insufficient_balance(client, services, monkeypatch):
    monkeypatch.setattr(services.accounts, "get_account",
                        lambda _id: {"user_id": 7, "account_status": "ACTIVE", "balance": 10})
    resp = client.post("/transactions/withdraw", json={"sender_account_id": 1001, "amount": 200})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "Insufficient balance"
    assert body["requested"] == 200.0
    assert body["balance"] == 10


# --------------------------------------------------------------------------- #
# POST /transactions/transfer                                                 #
# --------------------------------------------------------------------------- #
def _wire_transfer(services, monkeypatch, FakeResp, adjust):
    monkeypatch.setattr(
        services.accounts, "get_account",
        lambda aid: {"user_id": int(aid), "account_status": "ACTIVE", "balance": 1000.0},
    )
    monkeypatch.setattr(services.accounts, "adjust_balance", adjust)
    monkeypatch.setattr(services.db, "create_transaction",
                        lambda body: FakeResp({"transaction_id": 99, "status": "PENDING"}, 201))
    update = MagicMock()
    notify = MagicMock(return_value=True)
    monkeypatch.setattr(services.db, "update_transaction", update)
    monkeypatch.setattr(services.notify, "send", notify)
    return update, notify


def test_transfer_happy_path(client, services, monkeypatch, FakeResp):
    adjust = MagicMock(return_value=True)
    update, notify = _wire_transfer(services, monkeypatch, FakeResp, adjust)

    resp = client.post("/transactions/transfer",
                       json={"sender_account_id": 1, "receiver_account_id": 2, "amount": 100})

    assert resp.status_code == 201
    assert resp.get_json()["status"] == "COMPLETED"
    assert [c.args for c in adjust.call_args_list] == [(1, -100.0), (2, 100.0)]
    update.assert_called_once_with(99, {"status": "COMPLETED"})
    assert notify.call_count == 2                          # sender + receiver notified


def test_transfer_rejects_same_account(client):
    resp = client.post("/transactions/transfer",
                       json={"sender_account_id": 1, "receiver_account_id": 1, "amount": 100})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Cannot transfer money to the same account"


def test_transfer_requires_both_accounts(client):
    resp = client.post("/transactions/transfer", json={"sender_account_id": 1, "amount": 100})
    assert resp.status_code == 400


def test_transfer_rejects_insufficient_balance(client, services, monkeypatch):
    monkeypatch.setattr(
        services.accounts, "get_account",
        lambda aid: {"user_id": int(aid), "account_status": "ACTIVE", "balance": 10.0},
    )
    resp = client.post("/transactions/transfer",
                       json={"sender_account_id": 1, "receiver_account_id": 2, "amount": 100})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Insufficient balance to transfer"


def test_transfer_fails_when_debit_fails(client, services, monkeypatch, FakeResp):
    adjust = MagicMock(return_value=False)                 # sender debit fails
    update, notify = _wire_transfer(services, monkeypatch, FakeResp, adjust)

    resp = client.post("/transactions/transfer",
                       json={"sender_account_id": 1, "receiver_account_id": 2, "amount": 100})

    assert resp.status_code == 502
    assert "debit" in resp.get_json()["error"].lower()
    update.assert_called_once_with(99, {"status": "FAILED"})
    notify.assert_not_called()


def test_transfer_rolls_back_when_credit_fails(client, services, monkeypatch, FakeResp):
    adjust = MagicMock(side_effect=[True, False, True])    # debit ok, credit fails, rollback
    update, notify = _wire_transfer(services, monkeypatch, FakeResp, adjust)

    resp = client.post("/transactions/transfer",
                       json={"sender_account_id": 1, "receiver_account_id": 2, "amount": 100})

    assert resp.status_code == 502
    assert "rolled back" in resp.get_json()["error"].lower()
    assert [c.args for c in adjust.call_args_list] == [(1, -100.0), (2, 100.0), (1, 100.0)]
    update.assert_called_once_with(99, {"status": "FAILED"})


# --------------------------------------------------------------------------- #
# UPDATE / DELETE passthrough                                                  #
# --------------------------------------------------------------------------- #
def test_update_transaction_passthrough(client, services, monkeypatch, FakeResp):
    monkeypatch.setattr(services.db, "update_transaction",
                        lambda _id, body: FakeResp({"transaction_id": _id, **body}, 200))
    resp = client.put("/transactions/3", json={"status": "COMPLETED"})
    assert resp.status_code == 200
    assert resp.get_json() == {"transaction_id": 3, "status": "COMPLETED"}


def test_delete_transaction_forwards_query_params(client, services, monkeypatch, FakeResp):
    seen = {}

    def fake_delete(txn_id, params):
        seen["id"] = txn_id
        seen["params"] = params
        return FakeResp({"message": "gone", "mode": "hard"}, 200)

    monkeypatch.setattr(services.db, "delete_transaction", fake_delete)
    resp = client.delete("/transactions/3?hard=true")
    assert resp.status_code == 200
    assert seen == {"id": 3, "params": {"hard": "true"}}


# --------------------------------------------------------------------------- #
# HTMX UI endpoints                                                            #
# --------------------------------------------------------------------------- #
def _row(**over):
    base = {
        "transaction_id": 1, "transaction_type": "DEPOSIT", "amount": 100.0,
        "sender_account_id": None, "receiver_account_id": 1001,
        "status": "COMPLETED", "description": "x", "created_at": "2026-08-01 00:00:00",
    }
    base.update(over)
    return base


def test_ui_transactions_renders_table(client, services, monkeypatch, FakeResp):
    monkeypatch.setattr(services.db, "list_transactions",
                        lambda params: FakeResp({"transactions": [_row()]}, 200))
    resp = client.get("/ui/transactions")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "<table" in html
    assert 'id="txn-1"' in html


def test_ui_transactions_shows_alert_on_db_error(client, services, monkeypatch, FakeResp):
    monkeypatch.setattr(services.db, "list_transactions",
                        lambda params: FakeResp({"error": "boom"}, 500))
    resp = client.get("/ui/transactions")
    assert resp.status_code == 200
    assert "alert" in resp.get_data(as_text=True)


def test_ui_create_rejects_unknown_kind(client):
    resp = client.post("/ui/transactions/gift")
    assert resp.status_code == 200
    assert "Invalid transaction type" in resp.get_data(as_text=True)


def test_ui_create_deposit_returns_refreshed_table(client, services, monkeypatch, FakeResp, active_account):
    monkeypatch.setattr(services.accounts, "get_account", lambda _id: dict(active_account))
    monkeypatch.setattr(services.accounts, "adjust_balance", MagicMock(return_value=True))
    monkeypatch.setattr(services.db, "create_transaction",
                        lambda body: FakeResp({"transaction_id": 55, "status": "PENDING"}, 201))
    monkeypatch.setattr(services.db, "update_transaction", MagicMock())
    monkeypatch.setattr(services.notify, "send", MagicMock(return_value=True))
    monkeypatch.setattr(services.db, "list_transactions",
                        lambda params: FakeResp({"transactions": [_row(transaction_id=55)]}, 200))

    resp = client.post("/ui/transactions/deposit",
                       data={"receiver_account_id": "1001", "amount": "50"})

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "<table" in html
    assert 'id="txn-55"' in html
