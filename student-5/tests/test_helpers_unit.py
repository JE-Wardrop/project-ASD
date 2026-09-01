"""Unit tests for the small helper functions in the backend.

Covered:
  * routes/normal_ui.py  -> read_amount, check_account, announce, passthrough
  * services/accounts_api.py -> is_frozen, get_account, adjust_balance
"""

from unittest.mock import MagicMock

import pytest
import requests

from routes import normal_ui as nu
from services import accounts_api as acc


# --------------------------------------------------------------------------- #
# read_amount                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw, expected", [
    ("100", 100.0),
    (250, 250.0),
    (99.95, 99.95),
])
def test_read_amount_accepts_valid_numbers(raw, expected):
    amount, err = nu.read_amount({"amount": raw})
    assert err is None
    assert amount == expected


@pytest.mark.parametrize("raw", ["abc", None, "", "12x"])
def test_read_amount_rejects_non_numbers(raw):
    amount, err = nu.read_amount({"amount": raw})
    assert amount is None
    assert err == "Amount must be a number"


@pytest.mark.parametrize("raw", [0, -1, "-50"])
def test_read_amount_rejects_non_positive(raw):
    amount, err = nu.read_amount({"amount": raw})
    assert amount is None
    assert err == "Amount must be greater than 0"


# --------------------------------------------------------------------------- #
# check_account                                                               #
# --------------------------------------------------------------------------- #
def test_check_account_returns_account_when_active(monkeypatch):
    account = {"user_id": 7, "account_status": "ACTIVE", "balance": 500}
    monkeypatch.setattr(nu.accounts, "get_account", lambda _id: account)

    got, err = nu.check_account(1001, "Sender")
    assert err is None
    assert got is account


def test_check_account_skips_when_accounts_not_required(monkeypatch):
    monkeypatch.setattr(nu.accounts, "get_account", lambda _id: None)
    monkeypatch.setattr(nu.accounts, "REQUIRE_ACCOUNTS", False)

    got, err = nu.check_account(1001, "Sender")
    assert got is None
    assert err is None                       # soft-skip, no error


def test_check_account_errors_when_accounts_required(monkeypatch):
    monkeypatch.setattr(nu.accounts, "get_account", lambda _id: None)
    monkeypatch.setattr(nu.accounts, "REQUIRE_ACCOUNTS", True)

    got, err = nu.check_account(1001, "Sender")
    assert got is None
    assert err == "Sender account (1001) does not exist"


def test_check_account_rejects_frozen_account(monkeypatch):
    monkeypatch.setattr(
        nu.accounts, "get_account",
        lambda _id: {"account_status": "FROZEN", "user_id": 7},
    )
    got, err = nu.check_account(1001, "Receiver")
    assert got is None
    assert err == "Receiver account (1001) is in state FROZEN"


# --------------------------------------------------------------------------- #
# announce                                                                    #
# --------------------------------------------------------------------------- #
def test_announce_sends_notification_for_known_user(monkeypatch):
    send = MagicMock(return_value=True)
    monkeypatch.setattr(nu.notify, "send", send)

    nu.announce({"user_id": 42}, "hello")
    send.assert_called_once_with(42, "hello")


def test_announce_is_noop_without_account(monkeypatch):
    send = MagicMock()
    monkeypatch.setattr(nu.notify, "send", send)

    nu.announce(None, "hello")
    send.assert_not_called()


# --------------------------------------------------------------------------- #
# passthrough (needs an app context for jsonify)                              #
# --------------------------------------------------------------------------- #
def test_passthrough_forwards_json_and_status(backend_module, FakeResp):
    with backend_module.app.app_context():
        body, code = nu.passthrough(FakeResp({"transactions": []}, 200))
    assert code == 200
    assert body.get_json() == {"transactions": []}


def test_passthrough_maps_invalid_json_to_502(backend_module, FakeResp):
    with backend_module.app.app_context():
        body, code = nu.passthrough(FakeResp(ValueError("bad"), 200))
    assert code == 502
    assert body == {"error": "Database service returned invalid data"}


# --------------------------------------------------------------------------- #
# accounts_api.is_frozen                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("state", ["FROZEN", "frozen", "Closed", "suspended"])
def test_is_frozen_true_for_blocked_states(state):
    assert acc.is_frozen({"account_status": state}) is True


@pytest.mark.parametrize("account", [
    {"account_status": "ACTIVE"},
    {"account_status": ""},
    {},
])
def test_is_frozen_false_otherwise(account):
    assert acc.is_frozen(account) is False


# --------------------------------------------------------------------------- #
# accounts_api.get_account                                                    #
# --------------------------------------------------------------------------- #
def test_get_account_returns_json_on_success(monkeypatch, FakeResp):
    monkeypatch.setattr(
        acc.requests, "get",
        lambda url, timeout=None: FakeResp({"id": 1001, "balance": 10}, 200),
    )
    assert acc.get_account(1001) == {"id": 1001, "balance": 10}


def test_get_account_returns_none_when_service_unreachable(monkeypatch):
    def boom(*_a, **_k):
        raise requests.RequestException("connection refused")

    monkeypatch.setattr(acc.requests, "get", boom)
    assert acc.get_account(1001) is None


def test_get_account_returns_none_on_http_error(monkeypatch, FakeResp):
    monkeypatch.setattr(
        acc.requests, "get",
        lambda url, timeout=None: FakeResp({"error": "not found"}, 404),
    )
    assert acc.get_account(1001) is None


def test_get_account_returns_none_on_non_json_body(monkeypatch, FakeResp):
    monkeypatch.setattr(
        acc.requests, "get",
        lambda url, timeout=None: FakeResp(ValueError("no json"), 200),
    )
    assert acc.get_account(1001) is None


# --------------------------------------------------------------------------- #
# accounts_api.adjust_balance                                                 #
# --------------------------------------------------------------------------- #
def test_adjust_balance_true_on_2xx(monkeypatch, FakeResp):
    captured = {}

    def fake_patch(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResp({}, 200)

    monkeypatch.setattr(acc.requests, "patch", fake_patch)
    assert acc.adjust_balance(1001, -50) is True
    assert captured["json"] == {"delta": -50}
    assert captured["url"].endswith("/accounts/1001/balance")


def test_adjust_balance_false_on_http_error(monkeypatch, FakeResp):
    monkeypatch.setattr(
        acc.requests, "patch",
        lambda url, json=None, timeout=None: FakeResp({}, 400),
    )
    assert acc.adjust_balance(1001, 50) is False


def test_adjust_balance_false_when_service_unreachable(monkeypatch):
    def boom(*_a, **_k):
        raise requests.RequestException("timeout")

    monkeypatch.setattr(acc.requests, "patch", boom)
    assert acc.adjust_balance(1001, 50) is False
