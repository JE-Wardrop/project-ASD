import os
import sqlite3  
from flask import Flask, request, jsonify


# .../student-5/database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .../student-5/database/transactions.db (or via DB_PATH environment variable)
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "transactions.db"))

# .../student-5/database/schema.sql
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

# .../student-5/database/seed.sql
SEED_PATH = os.path.join(BASE_DIR, "seed.sql")

SERVICE_NAME = "student5-db"

app = Flask(__name__)

VALID_TYPES = {"DEPOSIT", "WITHDRAWAL", "TRANSFER"}
VALID_STATUSES = {"PENDING", "COMPLETED", "FAILED", "CANCELLED"}


# Init db
def init_db():
    #  check if database file exists, if not create it from schema.sql and seed.sql
    if os.path.exists(DB_PATH):
        print(f"Database file {DB_PATH} already exists, skip init_db()")    
        return
    
    print("Init database from schema.sql and seed.sql")
    
    # ensure the directory exists
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    
    try:
        # execute schema.sql and seed.sql
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            con.executescript(f.read())
        with open(SEED_PATH, encoding="utf-8") as f:
            con.executescript(f.read())
        con.commit()
        n = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        app.logger.info("Da tao database voi %d ban ghi", n)
    finally:
        con.close()

def get_conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def row_to_dict(row):
    return dict(row) if row is not None else None

@app.get("/health")
def health():
    try:
        con = get_conn()
        count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        con.close()
        return {"status": "ok", "service": SERVICE_NAME, "records": count}, 200
    except Exception as exc:
        return {"status": "error", "service": SERVICE_NAME, "detail": str(exc)}, 500

# READ
@app.get("/transactions")
def list_transactions():
    account_id = request.args.get("account_id", type=int)
    txn_type = request.args.get("type", type=str)
    status = request.args.get("status", type=str)
    limit = request.args.get("limit", default=100, type=int)
    
    # parameterized query, avoid SQL injection
    sql = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if account_id is not None:
        # filter by account_id in either sender_account_id or receiver_account_id
        sql += " AND (sender_account_id = ? OR receiver_account_id = ?)"
        params.extend([account_id, account_id])

    if txn_type:
        txn_type = txn_type.upper()
        if txn_type not in VALID_TYPES:
            return {"error": f"Invalid type. Type must be in: {sorted(VALID_TYPES)}"}, 400
        sql += " AND transaction_type = ?"
        params.append(txn_type)

    if status:
        status = status.upper()
        if status not in VALID_STATUSES:
            return {"error": f"Invalid status. Status must be in: {sorted(VALID_STATUSES)}"}, 400
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY created_at DESC, transaction_id DESC LIMIT ?"
    params.append(max(1, min(limit, 500))) 

    con = get_conn()
    rows = con.execute(sql, params).fetchall()
    con.close()

    return jsonify({
        "count": len(rows),
        "transactions": [row_to_dict(r) for r in rows],
    }), 200
    
    
@app.get("/transactions/<int:txn_id>")
def get_transaction(txn_id):
    con = get_conn()
    row = con.execute(
        "SELECT * FROM transactions WHERE transaction_id = ?", (txn_id,)
    ).fetchone()
    con.close()

    if row is None:
        return {"error": f"No transaction has found {txn_id}"}, 404
    return jsonify(row_to_dict(row)), 200

# CREATE
@app.post("/transactions")
def create_transaction():
#   Data validation, no backend logic
    data = request.get_json(silent=True) or {}

    txn_type = str(data.get("transaction_type", "")).upper()
    if txn_type not in VALID_TYPES:
        return {"error": f"transaction_type bat buoc, chi nhan: {sorted(VALID_TYPES)}"}, 400

    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return {"error": "amount bat buoc va phai la so"}, 400

    if amount <= 0:
        return {"error": "amount phai lon hon 0"}, 400

    status = str(data.get("status", "PENDING")).upper()
    if status not in VALID_STATUSES:
        return {"error": f"status khong hop le. Chi nhan: {sorted(VALID_STATUSES)}"}, 400

    sender = data.get("sender_account_id")
    receiver = data.get("receiver_account_id")

    con = get_conn()
    try:
        # add new transaction record to database
        cur = con.execute(
            """INSERT INTO transactions
                   (sender_account_id, receiver_account_id, transaction_type,
                    amount, currency, status, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sender, receiver, txn_type, amount,
             data.get("currency", "AUD"), status, data.get("description")),
        )
        con.commit()
        new_id = cur.lastrowid
        #  get the new record
        row = con.execute(
            "SELECT * FROM transactions WHERE transaction_id = ?", (new_id,)
        ).fetchone()
    except sqlite3.IntegrityError as exc:
        con.close()
        return {"error": "Vi pham rang buoc du lieu", "detail": str(exc)}, 400
    con.close()

    # 201 Created - standard REST status for creation
    return jsonify(row_to_dict(row)), 201

# Update
@app.put("/transactions/<int:txn_id>")
def update_transaction(txn_id):
    """Partial update.

    Only description and status can be edited. The amount and accounts
    of a recorded transaction cannot be changed - that's an accounting
    principle: to correct an amount, create a new adjustment
    transaction instead of editing history.

    updated_at is updated automatically via the TRIGGER in schema.sql.
    """
    data = request.get_json(silent=True) or {}

    fields, params = [], []

    if "description" in data:
        fields.append("description = ?")
        params.append(data["description"])

    if "status" in data:
        status = str(data["status"]).upper()
        if status not in VALID_STATUSES:
            return {"error": f"status khong hop le. Chi nhan: {sorted(VALID_STATUSES)}"}, 400
        fields.append("status = ?")
        params.append(status)

    if not fields:
        return {"error": "Khong co truong nao de cap nhat (chi nhan: description, status)"}, 400

    con = get_conn()
    exists = con.execute(
        "SELECT 1 FROM transactions WHERE transaction_id = ?", (txn_id,)
    ).fetchone()
    if exists is None:
        con.close()
        return {"error": f"Khong tim thay transaction {txn_id}"}, 404

    params.append(txn_id)
    con.execute(
        f"UPDATE transactions SET {', '.join(fields)} WHERE transaction_id = ?",
        params,
    )
    con.commit()
    row = con.execute(
        "SELECT * FROM transactions WHERE transaction_id = ?", (txn_id,)
    ).fetchone()
    con.close()

    return jsonify(row_to_dict(row)), 200


@app.delete("/transactions/<int:txn_id>")
def delete_transaction(txn_id):
    """Default is SOFT DELETE: change status to CANCELLED.

    Reason: in banking, nobody permanently deletes financial records -
    an audit trail must be kept for reconciliation. Matches the term
    'Cancel Transaction' in the feature registration form.

    Add ?hard=true for a permanent delete (used to demonstrate the D
    in CRUD in the demo video).
    """
    hard = request.args.get("hard", "false").lower() == "true"

    con = get_conn()
    row = con.execute(
        "SELECT * FROM transactions WHERE transaction_id = ?", (txn_id,)
    ).fetchone()
    if row is None:
        con.close()
        return {"error": f"Khong tim thay transaction {txn_id}"}, 404

    if hard:
        con.execute("DELETE FROM transactions WHERE transaction_id = ?", (txn_id,))
        con.commit()
        con.close()
        return {"message": f"Da xoa han transaction {txn_id}", "mode": "hard"}, 200

    if row["status"] == "COMPLETED":
        con.close()
        return {"error": "Khong the huy giao dich da COMPLETED"}, 409

    con.execute(
        "UPDATE transactions SET status = 'CANCELLED' WHERE transaction_id = ?",
        (txn_id,),
    )
    con.commit()
    updated = con.execute(
        "SELECT * FROM transactions WHERE transaction_id = ?", (txn_id,)
    ).fetchone()
    con.close()

    return jsonify({"message": f"Da huy transaction {txn_id}",
                    "mode": "soft",
                    "transaction": row_to_dict(updated)}), 200

if __name__ == "__main__":
    init_db()
    # Port 8000 is the team's shared convention: EVERY container listens
    # on 8000 inside the network. This container is mapped to host port 8305.
    app.run(host="0.0.0.0", port=8000, debug=True) 