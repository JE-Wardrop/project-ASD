import json
import sqlite3
from datetime import datetime 
from database.init_db import DATABASE_NAME
from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)
DATABASE_NAME = "/app/database/cm.db"


REQUIRED_FIELDS = [
    "card_holder_name",
    "card_number",
    "card_type",
    "expiry_date",
    "status"
]

VALID_STATUSES = {"Frozen", "Unfrozen"}


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

#was originally "database-service" this is what the agentic loop is calling it and I'm not sure why
@app.get("/")
def health():
    return jsonify({"service": "database", "status": "running"})


def _validate_payload(payload, partial=False):
    if partial:
        fields = [f for f in REQUIRED_FIELDS if f in payload]
        if not fields:
            return "At least one field is required for update."
    else:
        missing = [f for f in REQUIRED_FIELDS if f not in payload or payload[f] in (None, "")]
        if missing:
            return f"Missing required field(s): {', '.join(missing)}"

    if "status" in payload and payload["status"] not in VALID_STATUSES:
        return f"status must be one of {', '.join(sorted(VALID_STATUSES))}"

    return None



# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@app.post("/cards")
def create_card():
    payload = request.get_json(silent=True) or {}

    error = _validate_payload(payload, partial=False)
    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO cards (
            card_holder_name, card_number, card_type,
            expiry_date, status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload["card_holder_name"],
            payload["card_number"],
            payload["card_type"],
            payload["expiry_date"],
            payload["status"],
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid

    card = conn.execute(
        "SELECT card_id, card_holder_name, card_number, card_type, "
        "expiry_date, status FROM cards WHERE card_id = ?",
        (new_id,),
    ).fetchone()
    conn.close()

    return jsonify(dict(card)), 201


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

@app.get("/cards")
def get_cards():
    conn = get_db_connection()
    cards = conn.execute(
        "SELECT card_id, card_holder_name, card_number, card_type, "
        "expiry_date, status FROM cards"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in cards])


@app.get("/cards/<int:card_id>")
def get_card(card_id):
    conn = get_db_connection()
    card = conn.execute(
        "SELECT card_id, card_holder_name, card_number, card_type, "
        "expiry_date, status FROM cards WHERE card_id = ?",
        (card_id,),
    ).fetchone()
    conn.close()

    if card is None:
        return jsonify({"error": "Card not found"}), 404

    return jsonify(dict(card))


@app.get("/cards/by-type")
def get_cards_by_type():
    card_type = request.args.get("card_type", "").strip()

    if not card_type:
        return jsonify({"error": "card_type required"}), 400

    conn = get_db_connection()
    cards = conn.execute(
        "SELECT card_id, card_holder_name, card_number, card_type, "
        "expiry_date, status FROM cards WHERE card_type = ? COLLATE NOCASE",
        (card_type,),
    ).fetchall()
    conn.close()

    if not cards:
        return jsonify({"error": "No cards found"}), 404

    return jsonify([dict(row) for row in cards])


@app.get("/cards/by-status")
def get_cards_by_status():
    status = request.args.get("status", "").strip()

    if not status:
        return jsonify({"error": "status required"}), 400

    conn = get_db_connection()
    cards = conn.execute(
        "SELECT card_id, card_holder_name, card_number, card_type, "
        "expiry_date, status, credit_limit FROM cards WHERE status = ? COLLATE NOCASE",
        (status,),
    ).fetchall()
    conn.close()

    if not cards:
        return jsonify({"error": "No cards found"}), 404

    return jsonify([dict(row) for row in cards])


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@app.put("/cards/<int:card_id>")
def update_card(card_id):
    payload = request.get_json(silent=True) or {}

    error = _validate_payload(payload, partial=True)
    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM cards WHERE card_id = ?", (card_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Card not found"}), 404

    updated = dict(existing)
    for field in REQUIRED_FIELDS:
        if field in payload:
            updated[field] = payload[field]

    conn.execute(
        """
        UPDATE cards
        SET card_holder_name = ?, card_number = ?, card_type = ?,
            expiry_date = ?, status = ?, credit_limit = ?
        WHERE card_id = ?
        """,
        (
            updated["card_holder_name"],
            updated["card_number"],
            updated["card_type"],
            updated["expiry_date"],
            updated["status"],
            float(updated["credit_limit"]),
            card_id,
        ),
    )
    conn.commit()
    card = conn.execute(
        "SELECT card_id, card_holder_name, card_number, card_type, "
        "expiry_date, status, credit_limit FROM cards WHERE card_id = ?",
        (card_id,),
    ).fetchone()
    conn.close()

    return jsonify(dict(card)), 200



# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@app.delete("/cards/<int:card_id>")
def delete_card(card_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT card_id FROM cards WHERE card_id = ?", (card_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Card not found"}), 404

    conn.execute("DELETE FROM cards WHERE card_id = ?", (card_id,))
    conn.commit()
    conn.close()

    return jsonify({"deleted": card_id}), 200


# ---------------------------------------------------------------------------
# Freeze and Unfreeze
# ---------------------------------------------------------------------------



def freeze_card (card_number, account_holder, card_type, expiry_date,status):
    payload = request.get_json(silent=True) or {}

    error = _validate_payload(payload, partial=True)
    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    card_to_freeze = (
        '''SELECT * FROM cards
            WHERE status = Unfrozen
        ''')

    conn.execute("UPDATE FROM cards WHERE status = Frozen", (card_to_freeze))
    conn.commit()
    conn.close()
    


def unfreeze_card (card_number, account_holder, card_type, expiry_date,status):
    payload = request.get_json(silent=True) or {}

    error = _validate_payload(payload, partial=True)
    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    card_to_unfreeze = (
        '''SELECT * FROM cards
            WHERE status = Frozen
        ''')

    conn.execute("UPDATE FROM cards WHERE status = Unfrozen", (card_to_unfreeze))
    conn.commit()
    conn.close()




