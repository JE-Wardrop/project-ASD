# ---------------------------------------------------------------
# NEED TO FIND A WAY TO CONNECT app.py to cm_crud.py so that this code is 
# done in a containerisated method
# ---------------------------------------------------------------

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'cm.db')

# def get_db_connection():
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     return conn



# @app.get("/")
# def health():

#     #debug
#     conn = get_db_connection()
#     cards = conn.execute('SELECT * FROM cards').fetchall()
#     conn.close()
#     return jsonify([dict(card) for card in cards]), 200, jsonify({"service": "database", "status": "running"})
    
#     #normal
#     # return jsonify({"service": "database", "status": "running"})


# Try CRUD operations here at some point?


#DEBUG



REQUIRED_FIELDS = [
    "user_id",
    "card_number",
    "card_type",
    "expiry_date",
    "status",
    "balance"
]

VALID_STATUSES = {"Frozen", "Unfrozen"}

CARD_SELECT = """
    SELECT cards.card_id, cards.user_id, cards.card_number,
           cards.card_type, cards.expiry_date, cards.status, cards.balance
    FROM cards
"""


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

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

@app.post("/cards/create")
def create_card():

    # maybe something to do with this payload and json  format
    # The database cannot communicate with the backend 
    # The backend cannot communicate with the database

    payload = request.get_json(silent=True) or {}

    error = _validate_payload(payload, partial=False)
    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO cards (
            user_id, card_number, card_type, expiry_date, status, balance
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload["user_id"],
            payload["card_number"],
            payload["card_type"],
            payload["expiry_date"],
            payload["status"],
            payload["balance"],
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid

    card = conn.execute(
        "SELECT card_id, user_id, card_number, card_type, "
        "expiry_date, status, balance FROM cards WHERE card_id = ?",
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
        "SELECT card_id, user_id, card_number, card_type, "
        "expiry_date, status FROM cards"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in cards])


@app.get("/cards/<int:card_id>")
def get_card(card_id):
    conn = get_db_connection()
    card = conn.execute(
        "SELECT card_id, user_id, card_number, card_type, "
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
        "SELECT card_id, user_id, card_number, card_type, "
        "expiry_date, status FROM cards WHERE card_type = ? COLLATE NOCASE",
        (card_type,),
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
        SET user_id = ?, card_number = ?, card_type = ?,
            expiry_date = ?, status = ?, balance = ?
        WHERE card_id = ?
        """,
        (
            updated["user_id"],
            updated["card_number"],
            updated["card_type"],
            updated["expiry_date"],
            updated["status"],
            float(updated["balance"]),
            card_id,
        ),
    )

    conn.commit()
    card = conn.execute(
        "SELECT card_id, user_id, card_number, card_type, "
        "expiry_date, status, balance FROM cards WHERE card_id = ?",
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

def _set_status_by_card_number(card_number, new_status):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT card_id FROM cards WHERE card_number = ?", (card_number,)
    ).fetchone()

    if existing is None:
        conn.close()
        return None

    conn.execute("UPDATE cards SET status = ? WHERE card_number = ?", (new_status, card_number))
    conn.commit()
    card = conn.execute(CARD_SELECT + " WHERE cards.card_number = ?", (card_number,)).fetchone()
    conn.close()
    return card


@app.post("/cards/freeze")
def freeze_card():
    payload = request.get_json(silent=True) or request.form
    card_number = (payload.get("card_number") or "").strip()


    if not card_number:
        return jsonify({"error": "card_number is required"}), 400

    card = _set_status_by_card_number(card_number, "Frozen")
    if card is None:
        return jsonify({"error": "Card not found"}), 404

    return jsonify(dict(card)), 200


@app.post("/cards/unfreeze")
def unfreeze_card():
    payload = request.get_json(silent=True) or request.form
    card_number = (payload.get("card_number") or "").strip()
    

    if not card_number:
        return jsonify({"error": "card_number is required"}), 400

    card = _set_status_by_card_number(card_number, "Unfrozen")

    if card is None:
        return jsonify({"error": "Card not found"}), 404

    return jsonify(dict(card)), 200






#END OF DEBUG


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)