from flask import Blueprint, request, jsonify
from html import escape
from services.llm_client import call_transaction_agent
from services import database_api as db
ai_mode_bp = Blueprint("ai_mode", __name__)

SYSTEM_PROMPT = "transaction_system_prompt.txt"

def _panel(answer):
    return f'<div class="ai-answer"><h4>AI-Mode</h4><p>{escape(answer)}</p></div>'


def _alert(message, kind="warn"):
    return f'<div class="alert alert-{kind}">{escape(message)}</div>'


def _money(value):
    return f"${float(value or 0):,.2f} AUD"


def _format_transaction(txn):
    """Turn one transaction into readable text instead of JSON.

    Handing raw JSON to the model makes the model describe the JSON.
    Plain labelled lines keep it talking about the customer's money.
    """
    lines = [
        f"Transaction ID: {txn.get('transaction_id')}",
        f"Type: {txn.get('transaction_type')}",
        f"Amount: {_money(txn.get('amount'))}",
    ]
    if txn.get("sender_account_id") is not None:
        lines.append(f"From account: {txn['sender_account_id']}")
    if txn.get("receiver_account_id") is not None:
        lines.append(f"To account: {txn['receiver_account_id']}")

    lines.append(f"Status: {txn.get('status')}")
    lines.append(f"Date: {txn.get('created_at')}")

    if txn.get("description"):
        lines.append(f"Description: {txn['description']}")

    return "\n".join(lines)


def _summarise(rows, account_id):
    """Calculate the money-flow figures in Python, not in the model.

    A small LLM cannot reliably add up fifty records, and a wrong figure in a
    banking application is worse than no figure. The model receives only the
    finished numbers and is responsible for the wording, never the arithmetic.
    """
    account = int(account_id) if account_id else None

    money_in = money_out = 0.0
    completed = 0
    largest = None

    for txn in rows:
        # Only COMPLETED transactions have actually moved money
        if txn.get("status") != "COMPLETED":
            continue
        completed += 1

        amount = float(txn.get("amount") or 0)
        txn_type = txn.get("transaction_type")

        came_in = txn_type == "DEPOSIT" or (
            txn_type == "TRANSFER"
            and account is not None
            and txn.get("receiver_account_id") == account
        )
        went_out = txn_type == "WITHDRAWAL" or (
            txn_type == "TRANSFER"
            and account is not None
            and txn.get("sender_account_id") == account
        )

        if came_in:
            money_in += amount
        if went_out:
            money_out += amount

        if largest is None or amount > float(largest.get("amount") or 0):
            largest = txn

    label = account_id or "all accounts"

    if completed == 0:
        return f"Account: {label}\nCompleted transactions: 0"

    summary = [
        f"Account: {label}",
        f"Completed transactions: {completed}",
        f"Total money in: {_money(money_in)}",
        f"Total money out: {_money(money_out)}",
        f"Net change: {_money(money_in - money_out)}",
    ]

    if largest:
        summary.append(
            f"Largest single movement: {_money(largest.get('amount'))}, "
            f"{largest.get('transaction_type')}, described as "
            f"\"{largest.get('description') or 'no description'}\", "
            f"on {str(largest.get('created_at'))[:10]}"
        )

    return "\n".join(summary)

@ai_mode_bp.post("/transactions/<int:txn_id>/ai/explain")
def explain_transaction(txn_id):
    
    txn = db.get_transaction(txn_id)
    if txn is None:
        return _alert(f"Database service not working"), 503
    if txn.status_code == 404:
        return _alert("Transaction not found.", "error"), 404
    
    transaction = txn.json()
    try:
        answer = call_transaction_agent(
            SYSTEM_PROMPT,
            "explain_transaction_prompt.txt",
            _format_transaction(transaction),
            max_tokens=300
        )
    except Exception as e:
        return _alert(f"AI explanation failed: {str(e)}", "error"), 500
    return _panel(answer), 200

@ai_mode_bp.post("/ai/analyse")
def analyse_transactions():
    payload = request.form or (request.get_json(silent=True) or {})
    account_id = payload.get("account_id") or request.args.get("account_id")
    if account_id is not None:
        account_id = str(account_id).strip() or None

    
    params = {"limit": 50}
    if account_id:
        params["account_id"] = account_id
    
    resp = db.list_transactions(params)
    if resp is None:
        return _alert("Database service is not responding."), 503
    if resp.status_code >= 400:
        return _alert("Could not load transactions."), 502

    transactions = resp.json().get("transactions", [])
    
    if not transactions:
        return _alert("No transactions found for analysis."), 404

    try: 
        answer = call_transaction_agent(
            SYSTEM_PROMPT,
            "analyse_money_flow_prompt.txt",
            _summarise(transactions, account_id),
            max_tokens=400,
        )
    except Exception as exc:
        return _alert(f"AI-Mode is not available. Check Ollama is running. ({exc})"), 503

    return _panel(answer), 200  