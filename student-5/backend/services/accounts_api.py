import os
import requests

ACCOUNTS_URL = os.environ.get("ACCOUNTS_URL", "http://localhost:8302")

TIMEOUT = 5

REQUIRE_ACCOUNTS = os.environ.get("REQUIRE_ACCOUNTS", "false").lower() == "true"
FROZEN_STATES = {"FROZEN", "CLOSED", "SUSPENDED"}

def get_account(account_id):
    try:
        # call Accounts service to get account info
        resp = requests.get(f"{ACCOUNTS_URL}/accounts/{account_id}", timeout=TIMEOUT)
    except requests.RequestException as exc:
        print("Accounts service did not respond: %s", exc)
        if REQUIRE_ACCOUNTS:
            print(f"Accounts service did not respond: {exc}")
        return None

    if resp.status_code >= 400:
        print("Accounts returned %s for account %s", resp.status_code, account_id)
        return None
    try:
        return resp.json()
    except ValueError:
        return None

def is_frozen(account):
    return str(account.get("account_status", "")).upper() in FROZEN_STATES


def adjust_balance(account_id, delta):
    try:
        # call Accounts service to adjust balance
        resp = requests.patch(
            f"{ACCOUNTS_URL}/accounts/{account_id}/balance",
            json={"delta": delta},
            timeout=TIMEOUT,
        )
        if resp.status_code < 400:
            return True
        print("Balance update failed (%s)", resp.status_code)
        return False
    except requests.RequestException as exc:
        print("Could not reach Accounts to update balance: %s", exc)
        return False
    
