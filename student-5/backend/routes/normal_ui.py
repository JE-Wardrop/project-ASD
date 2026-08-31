from flask import Blueprint, request, jsonify

from services import database_api as db
from services import accounts_api as accounts
from services import notifications_api as notify

from views import html_formatters as fmt
bp = Blueprint("normal_ui", __name__)

def payload():
    # Try to read JSON payload first, then form data, then empty dict (since HTMX sends form data, not JSON)
    return request.get_json(silent=True) or request.form.to_dict() or {}

# unify return result from database service, including error handling
def passthrough(resp):
    try:
        return jsonify(resp.json()), resp.status_code
    except ValueError:
        return {"error": "Database service returned invalid data"}, 502

# validate amount 
def read_amount(data):
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return None, "Amount must be a number"
    if amount <= 0:
        return None, "Amount must be greater than 0"
    return amount, None

def check_account(account_id, label):
    # call accounts service to get account info
    account = accounts.get_account(account_id)
    if account is None:
        if accounts.REQUIRE_ACCOUNTS:
            return None, f"{label} account ({account_id}) does not exist"
        print("Skipping account check %s - Accounts not ready yet", account_id)
        return None, None
    if accounts.is_frozen(account):
        state = account.get("account_status")
        return None, f"{label} account ({account_id}) is in state {state}"
    return account, None
        
def announce(account, message):
    if account:
        # Call notifications service to send a notification to the user
        notify.send(account.get("user_id"), message)

# READ

# Return list of transactions, optionally filtered by query parameters (account_id, status, type)
@bp.get("/transactions")
def list_transactions():
    return passthrough(db.list_transactions(request.args.to_dict()))


# Return a single transaction by ID
@bp.get("/transactions/<int:txn_id>")
def get_transaction(txn_id):
    return passthrough(db.get_transaction(txn_id))

# Return list of transactions for a specific account, optionally filtered by query parameters (status, type)
@bp.get("/accounts/<int:account_id>/transactions")
def account_transactions(account_id):
    params = request.args.to_dict()
    params["account_id"] = account_id
    return passthrough(db.list_transactions(params))


# CREATE 
# @bp.post("/transactions")
# def create_transaction():
#     return passthrough(db.create_transaction(request.get_json(silent=True) or {}))

# API endpoint to make a deposit
@bp.post("/transactions/deposit")
def deposit():
    data = payload()
    receiver = data.get("receiver_account_id") or data.get("account_id")
    if receiver is None:
        return {"error": "receiver_account_id is required"}, 400

    # validate amount
    amount, err = read_amount(data)
    if err:
        return {"error": err}, 400
    # validate account exist
    account, err = check_account(receiver, "Receiver")
    if err:
        return {"error": err}, 400

    # call database service to create a transaction record with status PENDING]
    # Deposit -> no need sender account 
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
    #  call accounts service to adjust the balance of the receiver account
    ok = accounts.adjust_balance(receiver, amount) if account else True
    # update the transaction status to COMPLETED or FAILED based on the result of the balance adjustment
    txn["status"] = "COMPLETED" if ok else "FAILED"
    db.update_transaction(txn["transaction_id"], {"status": txn["status"]})

    # send a notification to the user about the deposit if the balance adjustment was successful
    if ok:
        announce(account, f"Deposit of ${amount:,.2f} AUD completed (txn #{txn['transaction_id']})")
    return jsonify(txn), 201 if ok else 502

@bp.post("/transactions/withdraw")
def withdraw():
    data = payload()
    sender = data.get("sender_account_id") or data.get("account_id")
    if sender is None:
        return {"error": "sender_account_id is required"}, 400

    amount, err = read_amount(data)
    if err:
        return {"error": err}, 400

    account, err = check_account(sender, "Sender")
    if err:
        return {"error": err}, 400

    # check if the sender account has sufficient balance for the withdrawal
    if account is not None and float(account.get("balance", 0)) < amount:
        return {"error": "Insufficient balance",
                "balance": account.get("balance"), "requested": amount}, 400

    # call database service to create a transaction record with status PENDING'
    # Withdrawal -> no need receiver account
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
    # call accounts service to adjust the balance of the sender account
    ok = accounts.adjust_balance(sender, -amount) if account else True
    # update the transaction status to COMPLETED or FAILED based on the result of the balance adjustment
    txn["status"] = "COMPLETED" if ok else "FAILED"
    db.update_transaction(txn["transaction_id"], {"status": txn["status"]})

    # send a notification to the user about the withdrawal if the balance adjustment was successful
    if ok:
        announce(account, f"Withdrawal of ${amount:,.2f} AUD completed (txn #{txn['transaction_id']})")
    return jsonify(txn), 201 if ok else 502


@bp.post("/transactions/transfer")
def transfer():
    """The most important flow - walk through these 7 steps in the video."""
    data = payload()
    sender = data.get("sender_account_id")
    receiver = data.get("receiver_account_id")

    # 1. Validate payload
    if sender is None or receiver is None:
        return {"error": "sender_account_id and receiver_account_id are both required"}, 400
    if sender == receiver:
        return {"error": "Cannot transfer money to the same account"}, 400

    amount, err = read_amount(data)
    if err:
        return {"error": err}, 400

    # 2. Check both accounts via the Accounts service API
    src, err = check_account(sender, "Sender")
    if err:
        return {"error": err}, 400
    dst, err = check_account(receiver, "Receiver")
    if err:
        return {"error": err}, 400

    # 3. Check sufficient balance
    if src is not None and float(src.get("balance", 0)) < amount:
        return {"error": "Insufficient balance to transfer",
                "balance": src.get("balance"), "requested": amount}, 400

    # 4. Record the transaction as PENDING
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

    # 5. Update both account balances
    if src is not None:
        # Case update balance of sender faild
        if not accounts.adjust_balance(sender, -amount):
            # call database service to update the transaction status to FAILED
            db.update_transaction(txn_id, {"status": "FAILED"})
            txn["status"] = "FAILED"
            return jsonify({"error": "Could not debit the source account",
                            "transaction": txn}), 502
        # Case update balance of receiver faild, need to rollback the sender's balance
        if not accounts.adjust_balance(receiver, amount):
            # Manual rollback: the two SQLite databases live in separate
            # services and cannot share a single transaction.
            
            # call accounts service to rollback the sender's balance
            accounts.adjust_balance(sender, amount)
            # call database service to update the transaction status to FAILED
            db.update_transaction(txn_id, {"status": "FAILED"})
            txn["status"] = "FAILED"
            return jsonify({"error": "Could not credit the destination account - rolled back",
                            "transaction": txn}), 502

    # 6. Finalize as COMPLETED
    db.update_transaction(txn_id, {"status": "COMPLETED"})
    txn["status"] = "COMPLETED"

    # 7. Notifications - best effort, never blocking
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

# UI endpoint for listing transactions via HTMX
@bp.get("/ui/transactions")
def ui_transactions():
    resp = db.list_transactions(request.args.to_dict())
    if resp.status_code >= 400:
        return fmt.alert("Could not load the transaction list"), 200
    return fmt.transactions_table(resp.json().get("transactions", [])), 200

# UI endpoint for deleting a transaction via HTMX
@bp.delete("/ui/transactions/<int:txn_id>")
def ui_delete(txn_id):
    db.delete_transaction(txn_id)
    resp = db.list_transactions({"limit": 100})
    return fmt.transactions_table(resp.json().get("transactions", [])), 200

# UI endpoints for creating transactions via HTMX
@bp.post("/ui/transactions/<string:kind>")
def ui_create(kind):
    handlers = {"deposit": deposit, "withdraw": withdraw, "transfer": transfer}
    if kind not in handlers:
        return fmt.alert("Invalid transaction type"), 200

    result = handlers[kind]()
    body, code = result if isinstance(result, tuple) else (result, 200)

    if code >= 400:
        # ensure data is a dictionary, whether body is a Response or a dict
        data = body.get_json() if hasattr(body, "get_json") else body
        return fmt.alert(data.get("error", "Transaction failed")), 200

    rows = db.list_transactions({"limit": 100}).json().get("transactions", [])
    return fmt.transactions_table(rows), 200