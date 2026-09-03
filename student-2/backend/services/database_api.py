import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://student2-database:5002")

TIMEOUT = 5


def get_accounts():
    response = requests.get(f"{DATABASE_SERVICE_URL}/accounts", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_account_response(account_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/accounts/{account_id}", timeout=TIMEOUT)


def get_accounts_by_user_response(user_id):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/accounts/by-user",
        params={"user_id": user_id},
        timeout=TIMEOUT,
    )


def get_accounts_by_status_response(status):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/accounts/by-status",
        params={"status": status},
        timeout=TIMEOUT,
    )


def get_account_balance_response(account_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/accounts/{account_id}/balance", timeout=TIMEOUT)


def create_account_response(payload):
    return requests.post(f"{DATABASE_SERVICE_URL}/accounts", json=payload, timeout=TIMEOUT)


def update_account_response(account_id, payload):
    return requests.put(f"{DATABASE_SERVICE_URL}/accounts/{account_id}", json=payload, timeout=TIMEOUT)


def adjust_balance_response(account_id, delta):
    return requests.patch(
        f"{DATABASE_SERVICE_URL}/accounts/{account_id}/balance",
        json={"delta": delta},
        timeout=TIMEOUT,
    )


def freeze_account_response(account_id):
    return requests.post(f"{DATABASE_SERVICE_URL}/accounts/{account_id}/freeze", timeout=TIMEOUT)


def unfreeze_account_response(account_id):
    return requests.post(f"{DATABASE_SERVICE_URL}/accounts/{account_id}/unfreeze", timeout=TIMEOUT)


def close_account_response(account_id):
    return requests.post(f"{DATABASE_SERVICE_URL}/accounts/{account_id}/close", timeout=TIMEOUT)


def delete_account_response(account_id):
    return requests.delete(f"{DATABASE_SERVICE_URL}/accounts/{account_id}", timeout=TIMEOUT)
