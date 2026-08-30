"""Sinh HTML fragment cho HTMX.

HTMX khong doi JSON - no nhan HTML roi nhet thang vao DOM.
Tach viec sinh HTML ra day de routes/ chi lo dieu huong.
"""
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
        <button hx-post="{BACKEND}/ui/transactions/{txn['transaction_id']}/ai/explain"
            hx-target="#ai-output" hx-swap="innerHTML">Explain</button>
    <button hx-delete="{BACKEND}/ui/transactions/{txn['transaction_id']}"
            hx-target="#table-area" hx-swap="innerHTML"
            hx-confirm="Huy giao dich nay?">Cancel</button>
  </td>
</tr>"""


def transactions_table(rows):
    if not rows:
        return '<table id="txn-table"><tbody><tr><td>Khong co giao dich nao.</td></tr></tbody></table>'
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