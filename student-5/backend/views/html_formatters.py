import os
from html import escape

BACKEND = os.environ.get("BACKEND_URL", "http://localhost:8205")

STATUS_CLASS = {
    "COMPLETED": "pill pill-ok",
    "PENDING": "pill pill-wait",
    "FAILED": "pill pill-bad",
    "CANCELLED": "pill pill-muted",
}


def _cell(value):
    return escape(str(value)) if value is not None else "&mdash;"


# A COMPLETED transaction needs no explanation - the row already shows the
# type, amount, accounts and date. The states a customer actually asks about
# are the ones where the money did not move as expected.
EXPLAINABLE_STATUSES = {"PENDING", "FAILED", "CANCELLED"}


def _explain_button(txn):
    """Offer AI-Mode only where it answers a real customer question."""
    if txn.get("status") not in EXPLAINABLE_STATUSES:
        return ""
    return (
        f'<button hx-post="{BACKEND}/transactions/{txn["transaction_id"]}/ai/explain"\n'
        f'            hx-target="#ai-output" hx-swap="innerHTML">Explain</button>'
    )


def transaction_row(txn):
    status = txn.get("status", "")
    return f"""
<tr id="txn-{txn['transaction_id']}">
  <td class="num">{txn['transaction_id']}</td>
  <td>{_cell(txn.get('transaction_type'))}</td>
  <td class="num">${float(txn.get('amount', 0)):,.2f}</td>
  <td class="num">{_cell(txn.get('sender_account_id'))}</td>
  <td class="num">{_cell(txn.get('receiver_account_id'))}</td>
  <td><span class="{STATUS_CLASS.get(status, 'pill')}">{_cell(status)}</span></td>
  <td>{_cell(txn.get('description'))}</td>
  <td class="num">{_cell(txn.get('created_at'))}</td>
  <td>
    <div class="row-actions">
      {_explain_button(txn)}
      <button hx-delete="{BACKEND}/ui/transactions/{txn['transaction_id']}"
              hx-target="#table-area" hx-swap="innerHTML"
              hx-confirm="Cancel this transaction?">Cancel</button>
    </div>
  </td>
</tr>"""


def transactions_table(rows):
    if not rows:
        return '<table id="txn-table"><tbody><tr><td>No transactions.</td></tr></tbody></table>'
    body = "".join(transaction_row(r) for r in rows)
    return f"""
<table id="txn-table">
  <thead>
    <tr><th>ID</th><th>Type</th><th>Amount</th><th>From</th><th>To</th>
        <th>Status</th><th>Description</th><th>Created</th><th></th></tr>
  </thead>
  <tbody>{body}</tbody>
</table>"""


def alert(message, kind="error"):
    return f'<div class="alert alert-{escape(kind)}">{escape(str(message))}</div>'


def ai_panel(text):
    return f'<div class="ai-answer"><h4>AI-Mode</h4><p>{escape(text)}</p></div>'