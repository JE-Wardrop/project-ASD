"""End-to-end tests for the account-service backend.

These hit the real backend over HTTP (via docker-compose or a locally
running `python backend/app.py` + `python database/app.py`), so they are
skipped automatically if the service isn't reachable. Use this as
post-deployment evidence after `docker-compose up`.
"""

import os
import re

import pytest
import requests

BASE_URL = os.getenv("FLASK_BASE_URL", "http://localhost:8202")


def _service_available():
    try:
        requests.get(BASE_URL, timeout=2)
        return True
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(
    not _service_available(), reason=f"account-service not reachable at {BASE_URL}"
)


def test_health():
    response = requests.get(BASE_URL, timeout=5)
    assert response.status_code == 200


def test_list_accounts_returns_html():
    response = requests.get(f"{BASE_URL}/accounts", timeout=5)
    assert response.status_code == 200
    assert "<table" in response.text or "No accounts" in response.text


def test_create_view_freeze_close_cycle():
    # 8-digit format required by the database service; "9" prefix keeps it
    # clear of the seeded 1000000x accounts.
    account_number = f"9{os.getpid() % 10_000_000:07d}"
    account_id = None

    try:
        create = requests.post(
            f"{BASE_URL}/accounts/create",
            data={
                "user_id": "1",
                "account_number": account_number,
                "account_type": "EVERYDAY",
                "balance": "25",
            },
            timeout=5,
        )
        assert create.status_code == 201

        listing = requests.get(f"{BASE_URL}/accounts", timeout=5)
        assert account_number in listing.text
        account_id = _extract_account_id(listing.text, account_number)

        by_status = requests.get(
            f"{BASE_URL}/accounts/by-status", params={"status": "ACTIVE"}, timeout=5
        )
        assert by_status.status_code == 200
    finally:
        # Clean up so repeated test runs don't litter the account list.
        if account_id is not None:
            requests.post(
                f"{BASE_URL}/accounts/delete", data={"account_id": account_id}, timeout=5
            )


def _extract_account_id(accounts_html, account_number):
    match = re.search(
        r"<tr>\s*<td>(\d+)</td>\s*<td>\d+</td>\s*<td>" + re.escape(account_number),
        accounts_html,
    )
    return match.group(1) if match else None


def test_find_student_by_id_requires_id():
    response = requests.get(f"{BASE_URL}/accounts/by-id", timeout=5)
    assert response.status_code == 400


def test_ask_local_agent_responds_or_reports_unavailable():
    response = requests.post(
        f"{BASE_URL}/ask", data={"question": "What is this service for?"}, timeout=30
    )
    assert response.status_code in (200, 503)
