from flask import Blueprint, request, jsonify

from services import database_api as db
from services import accounts_api as accounts
from services import notifications_api as notify

from views import html_formatters as fmt
bp = Blueprint("normal_ui", __name__)

def payload():
    """HTMX gui form-encoded, curl gui JSON. Nhan ca hai."""
    return request.get_json(silent=True) or request.form.to_dict() or {}

def passthrough(resp):
    try:
        return jsonify(resp.json()), resp.status_code
    except ValueError:
        return {"error": "Database service tra ve du lieu khong hop le"}, 502
    
def read_amount(data):
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return None, "amount bat buoc va phai la so"
    if amount <= 0:
        return None, "amount phai lon hon 0"
    return amount, None

def check_account(account_id, label):
    """(account, loi). account=None + loi=None => bo qua kiem tra."""
    account = accounts.get_account(account_id)
    if account is None:
        if accounts.REQUIRE_ACCOUNTS:
            return None, f"Tai khoan {label} ({account_id}) khong ton tai"
        print("Bo qua kiem tra account %s - Accounts chua san sang", account_id)
        return None, None
    if accounts.is_frozen(account):
        state = account.get("account_status")
        return None, f"Tai khoan {label} ({account_id}) dang o trang thai {state}"
    return account, None
        
def announce(account, message):
    if account:
        notify.send(account.get("user_id"), message)

# READ
@bp.get("/transactions")
def list_transactions():
    return passthrough(db.list_transactions(request.args.to_dict()))


@bp.get("/transactions/<int:txn_id>")
def get_transaction(txn_id):
    return passthrough(db.get_transaction(txn_id))


@bp.get("/accounts/<int:account_id>/transactions")
def account_transactions(account_id):
    params = request.args.to_dict()
    params["account_id"] = account_id
    return passthrough(db.list_transactions(params))

# CREATE 
def create_transaction():
    return passthrough(db.create_transaction(request.get_json(silent=True) or {}))
@bp.post("/transactions/deposit")
def deposit():
    data = payload()
    receiver = data.get("receiver_account_id") or data.get("account_id")
    if receiver is None:
        return {"error": "receiver_account_id bat buoc"}, 400

    amount, err = read_amount(data)
    if err:
        return {"error": err}, 400

    account, err = check_account(receiver, "nhan")
    if err:
        return {"error": err}, 400

    created = db.create_transaction({
        "transaction_type": "DEPOSIT",
        "receiver_account_id": receiver,
        "amount": amount,
        "description": data.get("description", "Deposit"),
        "status": "PENDING",
    })
    if created.status_code >= 400:
        return passthrough(created)

    txn = created.json()
    ok = accounts.adjust_balance(receiver, amount) if account else True
    txn["status"] = "COMPLETED" if ok else "FAILED"
    db.update_transaction(txn["transaction_id"], {"status": txn["status"]})

    if ok:
        announce(account, f"Deposit of ${amount:,.2f} AUD completed (txn #{txn['transaction_id']})")
    return jsonify(txn), 201 if ok else 502

@bp.post("/transactions/withdraw")
def withdraw():
    data = payload()
    sender = data.get("sender_account_id") or data.get("account_id")
    if sender is None:
        return {"error": "sender_account_id bat buoc"}, 400

    amount, err = read_amount(data)
    if err:
        return {"error": err}, 400

    account, err = check_account(sender, "gui")
    if err:
        return {"error": err}, 400

    if account is not None and float(account.get("balance", 0)) < amount:
        return {"error": "Khong du so du",
                "balance": account.get("balance"), "requested": amount}, 400

    created = db.create_transaction({
        "transaction_type": "WITHDRAWAL",
        "sender_account_id": sender,
        "amount": amount,
        "description": data.get("description", "Withdrawal"),
        "status": "PENDING",
    })
    if created.status_code >= 400:
        return passthrough(created)

    txn = created.json()
    ok = accounts.adjust_balance(sender, -amount) if account else True
    txn["status"] = "COMPLETED" if ok else "FAILED"
    db.update_transaction(txn["transaction_id"], {"status": txn["status"]})

    if ok:
        announce(account, f"Withdrawal of ${amount:,.2f} AUD completed (txn #{txn['transaction_id']})")
    return jsonify(txn), 201 if ok else 502


@bp.post("/transactions/transfer")
def transfer():
    """Luong quan trong nhat - thuyet minh dung 7 buoc nay trong video."""
    data = payload()
    sender = data.get("sender_account_id")
    receiver = data.get("receiver_account_id")

    # 1. Validate payload
    if sender is None or receiver is None:
        return {"error": "sender_account_id va receiver_account_id deu bat buoc"}, 400
    if sender == receiver:
        return {"error": "Khong the chuyen tien cho chinh tai khoan do"}, 400

    amount, err = read_amount(data)
    if err:
        return {"error": err}, 400

    # 2. Kiem tra hai tai khoan qua API cua Binh
    src, err = check_account(sender, "gui")
    if err:
        return {"error": err}, 400
    dst, err = check_account(receiver, "nhan")
    if err:
        return {"error": err}, 400

    # 3. Kiem tra du so du
    if src is not None and float(src.get("balance", 0)) < amount:
        return {"error": "Khong du so du de chuyen",
                "balance": src.get("balance"), "requested": amount}, 400

    # 4. Ghi giao dich PENDING
    created = db.create_transaction({
        "transaction_type": "TRANSFER",
        "sender_account_id": sender,
        "receiver_account_id": receiver,
        "amount": amount,
        "description": data.get("description", "Transfer"),
        "status": "PENDING",
    })
    if created.status_code >= 400:
        return passthrough(created)

    txn = created.json()
    txn_id = txn["transaction_id"]

    # 5. Cap nhat balance hai ben
    if src is not None:
        if not accounts.adjust_balance(sender, -amount):
            db.update_transaction(txn_id, {"status": "FAILED"})
            txn["status"] = "FAILED"
            return jsonify({"error": "Khong tru duoc tien tai khoan nguon",
                            "transaction": txn}), 502

        if not accounts.adjust_balance(receiver, amount):
            # Hoan tac thu cong: hai SQLite o hai service khac nhau
            # khong the nam trong mot transaction chung.
            accounts.adjust_balance(sender, amount)
            db.update_transaction(txn_id, {"status": "FAILED"})
            txn["status"] = "FAILED"
            return jsonify({"error": "Khong cong duoc tien tai khoan dich - da hoan tac",
                            "transaction": txn}), 502

    # 6. Chot COMPLETED
    db.update_transaction(txn_id, {"status": "COMPLETED"})
    txn["status"] = "COMPLETED"

    # 7. Thong bao - best effort, khong bao gio chan
    announce(src, f"You sent ${amount:,.2f} AUD to account {receiver} (txn #{txn_id})")
    announce(dst, f"You received ${amount:,.2f} AUD from account {sender} (txn #{txn_id})")

    return jsonify(txn), 201
# UPDATE
@bp.put("/transactions/<int:txn_id>")
def update_transaction(txn_id):
    return passthrough(db.update_transaction(txn_id, request.get_json(silent=True) or {}))


# DELETE
@bp.delete("/transactions/<int:txn_id>")
def delete_transaction(txn_id):
    return passthrough(db.delete_transaction(txn_id, request.args.to_dict()))

# dont know what this is for, maybe for testing purposes
@bp.get("/ui/transactions")
def ui_transactions():
    resp = db.list_transactions(request.args.to_dict())
    if resp.status_code >= 400:
        return fmt.alert("Khong tai duoc danh sach giao dich"), 200
    return fmt.transactions_table(resp.json().get("transactions", [])), 200


@bp.delete("/ui/transactions/<int:txn_id>")
def ui_delete(txn_id):
    db.delete_transaction(txn_id)
    resp = db.list_transactions({"limit": 100})
    return fmt.transactions_table(resp.json().get("transactions", [])), 200

@bp.post("/ui/transactions/<string:kind>")
def ui_create(kind):
    """Nhan form tu HTMX, tra ve bang da lam moi hoac thong bao loi."""
    handlers = {"deposit": deposit, "withdraw": withdraw, "transfer": transfer}
    if kind not in handlers:
        return fmt.alert("Loai giao dich khong hop le"), 200

    result = handlers[kind]()
    body, code = result if isinstance(result, tuple) else (result, 200)

    if code >= 400:
        data = body.get_json() if hasattr(body, "get_json") else body
        return fmt.alert(data.get("error", "Giao dich that bai")), 200

    rows = db.list_transactions({"limit": 100}).json().get("transactions", [])
    return fmt.transactions_table(rows), 200