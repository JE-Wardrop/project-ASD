"""API tests for the database service (database/app.py).

Each test runs against a fresh SQLite file built from schema.sql + seed.sql
(14 seed rows).  Only HTTP behaviour is asserted - no mocking.
"""

SEED_COUNT = 14


def _post_deposit(db_client, **over):
    body = {"transaction_type": "DEPOSIT", "receiver_account_id": 1001, "amount": 10}
    body.update(over)
    return db_client.post("/transactions", json=body)


# --------------------------------------------------------------------------- #
# /health                                                                     #
# --------------------------------------------------------------------------- #
def test_health_reports_record_count(db_client):
    resp = db_client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["records"] == SEED_COUNT


# --------------------------------------------------------------------------- #
# GET /transactions                                                           #
# --------------------------------------------------------------------------- #
def test_list_returns_all_seed_rows(db_client):
    data = db_client.get("/transactions").get_json()
    assert data["count"] == SEED_COUNT
    assert len(data["transactions"]) == SEED_COUNT


def test_list_orders_by_created_at_desc(db_client):
    rows = db_client.get("/transactions").get_json()["transactions"]
    stamps = [r["created_at"] for r in rows]
    assert stamps == sorted(stamps, reverse=True)


def test_list_filter_by_account_matches_sender_or_receiver(db_client):
    rows = db_client.get("/transactions?account_id=1001").get_json()["transactions"]
    assert rows                                    # seed has activity on 1001
    for r in rows:
        assert 1001 in (r["sender_account_id"], r["receiver_account_id"])


def test_list_filter_by_type_is_case_insensitive(db_client):
    rows = db_client.get("/transactions?type=deposit").get_json()["transactions"]
    assert rows
    assert {r["transaction_type"] for r in rows} == {"DEPOSIT"}


def test_list_filter_by_status(db_client):
    rows = db_client.get("/transactions?status=failed").get_json()["transactions"]
    assert {r["status"] for r in rows} == {"FAILED"}


def test_list_limit_is_respected(db_client):
    data = db_client.get("/transactions?limit=3").get_json()
    assert data["count"] == 3


def test_list_rejects_unknown_type(db_client):
    resp = db_client.get("/transactions?type=BOGUS")
    assert resp.status_code == 400
    assert "Invalid type" in resp.get_json()["error"]


def test_list_rejects_unknown_status(db_client):
    resp = db_client.get("/transactions?status=BOGUS")
    assert resp.status_code == 400
    assert "Invalid status" in resp.get_json()["error"]


# --------------------------------------------------------------------------- #
# GET /transactions/<id>                                                      #
# --------------------------------------------------------------------------- #
def test_get_single_transaction(db_client):
    resp = db_client.get("/transactions/1")
    assert resp.status_code == 200
    assert resp.get_json()["transaction_id"] == 1


def test_get_missing_transaction_is_404(db_client):
    resp = db_client.get("/transactions/9999")
    assert resp.status_code == 404
    assert "9999" in resp.get_json()["error"]


# --------------------------------------------------------------------------- #
# POST /transactions                                                          #
# --------------------------------------------------------------------------- #
def test_create_deposit_defaults_currency_and_status(db_client):
    resp = _post_deposit(db_client, amount=123.45)
    assert resp.status_code == 201
    row = resp.get_json()
    assert row["transaction_id"] > SEED_COUNT
    assert row["transaction_type"] == "DEPOSIT"
    assert row["currency"] == "AUD"
    assert row["status"] == "PENDING"
    assert row["sender_account_id"] is None


def test_create_persists_row(db_client):
    new_id = _post_deposit(db_client).get_json()["transaction_id"]
    assert db_client.get("/transactions").get_json()["count"] == SEED_COUNT + 1
    assert db_client.get(f"/transactions/{new_id}").status_code == 200


def test_create_rejects_unknown_type(db_client):
    resp = _post_deposit(db_client, transaction_type="GIFT")
    assert resp.status_code == 400


def test_create_rejects_non_numeric_amount(db_client):
    resp = _post_deposit(db_client, amount="lots")
    assert resp.status_code == 400


def test_create_rejects_non_positive_amount(db_client):
    resp = _post_deposit(db_client, amount=0)
    assert resp.status_code == 400


def test_create_rejects_unknown_status(db_client):
    resp = _post_deposit(db_client, status="ALMOST")
    assert resp.status_code == 400


def test_create_rejects_constraint_violation(db_client):
    # DEPOSIT with a sender_account_id violates the schema CHECK.
    resp = _post_deposit(db_client, sender_account_id=1002)
    assert resp.status_code == 400
    assert "constraint" in resp.get_json()["error"].lower()


# --------------------------------------------------------------------------- #
# PUT /transactions/<id>                                                      #
# --------------------------------------------------------------------------- #
def test_update_description_and_status(db_client):
    resp = db_client.put("/transactions/4", json={"description": "edited", "status": "completed"})
    assert resp.status_code == 200
    row = resp.get_json()
    assert row["description"] == "edited"
    assert row["status"] == "COMPLETED"


def test_update_bumps_updated_at(db_client):
    before = db_client.get("/transactions/4").get_json()["updated_at"]
    db_client.put("/transactions/4", json={"description": "touch"})
    after = db_client.get("/transactions/4").get_json()["updated_at"]
    assert after >= before          # trigger keeps updated_at current


def test_update_rejects_empty_body(db_client):
    resp = db_client.put("/transactions/4", json={})
    assert resp.status_code == 400


def test_update_rejects_bad_status(db_client):
    resp = db_client.put("/transactions/4", json={"status": "NOPE"})
    assert resp.status_code == 400


def test_update_missing_transaction_is_404(db_client):
    resp = db_client.put("/transactions/9999", json={"description": "x"})
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# DELETE /transactions/<id>                                                   #
# --------------------------------------------------------------------------- #
def test_soft_delete_sets_status_cancelled(db_client):
    # row 4 is a PENDING deposit in the seed data
    resp = db_client.delete("/transactions/4")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["mode"] == "soft"
    assert body["transaction"]["status"] == "CANCELLED"


def test_cannot_soft_delete_completed_transaction(db_client):
    # row 1 is COMPLETED in the seed data
    resp = db_client.delete("/transactions/1")
    assert resp.status_code == 409


def test_hard_delete_removes_row(db_client):
    new_id = _post_deposit(db_client).get_json()["transaction_id"]
    resp = db_client.delete(f"/transactions/{new_id}?hard=true")
    assert resp.status_code == 200
    assert resp.get_json()["mode"] == "hard"
    assert db_client.get(f"/transactions/{new_id}").status_code == 404


def test_delete_missing_transaction_is_404(db_client):
    resp = db_client.delete("/transactions/9999")
    assert resp.status_code == 404
