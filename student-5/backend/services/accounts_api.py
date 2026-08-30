import os
import requests

ACCOUNTS_URL = os.environ.get("ACCOUNTS_URL", "http://localhost:8202")

TIMEOUT = 5

REQUIRE_ACCOUNTS = os.environ.get("REQUIRE_ACCOUNTS", "false").lower() == "true"
FROZEN_STATES = {"FROZEN", "CLOSED", "SUSPENDED"}

def get_account(account_id):
    """Tra ve dict tai khoan, hoac None neu khong tim thay / khong goi duoc."""
    try:
        resp = requests.get(f"{ACCOUNTS_URL}/accounts/{account_id}", timeout=TIMEOUT)
    except requests.RequestException as exc:
        print("Accounts service khong phan hoi: %s", exc)
        if REQUIRE_ACCOUNTS:
            print(f"Accounts service khong phan hoi: {exc}")
        return None

    if resp.status_code >= 400:
        print("Accounts tra ve %s cho account %s", resp.status_code, account_id)
        return None
    try:
        return resp.json()
    except ValueError:
        return None

def is_frozen(account):
    return str(account.get("account_status", "")).upper() in FROZEN_STATES


def adjust_balance(account_id, delta):
    """delta am = tru tien. Tra ve True/False, khong nem exception."""
    try:
        resp = requests.patch(
            f"{ACCOUNTS_URL}/accounts/{account_id}/balance",
            json={"delta": delta},
            timeout=TIMEOUT,
        )
        if resp.status_code < 400:
            return True
        print("Cap nhat balance that bai (%s)", resp.status_code)
        return False
    except requests.RequestException as exc:
        print("Khong goi duoc Accounts de cap nhat balance: %s", exc)
        return False
    
