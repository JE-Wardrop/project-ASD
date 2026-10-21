import os

import requests

# Cloud (deploy-azure.sh) sets DATABASE_SERVICE_URL. Compose and the backend Dockerfile
# set DB_URL=http://student5-db:8000, a name that only exists inside Docker Compose,
# so the cloud value must win.
DB_URL = os.environ.get("DATABASE_SERVICE_URL") or os.environ.get("DB_URL", "http://localhost:8305")

TIMEOUT = 5
def _request(method, path, **kwargs):
    """The Database is a HARD dependency - nothing works without it."""
    try:
        return requests.request(method, f"{DB_URL}{path}", timeout=TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(f"Database service did not respond: {exc}") from exc
        
def health():
    return _request("GET", "/health")

def list_transactions(params=None):
    return _request("GET", "/transactions", params=params or {})

def get_transaction(txn_id):
    return _request("GET", f"/transactions/{txn_id}")

def create_transaction(payload):
    return _request("POST", "/transactions", json=payload)

def update_transaction(txn_id, payload):
    return _request("PUT", f"/transactions/{txn_id}", json=payload)

def delete_transaction(txn_id, params=None):
    return _request("DELETE", f"/transactions/{txn_id}", params=params or {})