"""Unit tests for views/html_formatters.py (pure functions, no Flask needed)."""

from views import html_formatters as fmt


def _txn(**over):
    base = {
        "transaction_id": 1,
        "transaction_type": "TRANSFER",
        "amount": 1234.5,
        "sender_account_id": 1001,
        "receiver_account_id": 1002,
        "status": "COMPLETED",
        "description": "Rent share",
        "created_at": "2026-08-14 10:00:00",
    }
    base.update(over)
    return base


def test_cell_renders_dash_for_none():
    assert fmt._cell(None) == "&mdash;"


def test_cell_escapes_html():
    out = fmt._cell("<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_transaction_row_contains_core_fields():
    row = fmt.transaction_row(_txn())
    assert 'id="txn-1"' in row
    assert "TRANSFER" in row
    assert "$1,234.50" in row          # amount formatted with thousands + 2dp
    assert "1001" in row and "1002" in row
    assert "pill pill-ok" in row       # COMPLETED -> ok pill


def test_transaction_row_unknown_status_uses_default_pill():
    row = fmt.transaction_row(_txn(status="WEIRD"))
    assert 'class="pill"' in row       # falls back to bare pill class
    assert "WEIRD" in row


def test_transaction_row_missing_optional_field_shows_dash():
    row = fmt.transaction_row(_txn(description=None))
    assert "&mdash;" in row


def test_transactions_table_empty():
    out = fmt.transactions_table([])
    assert "No transactions." in out


def test_transactions_table_renders_one_row_per_txn():
    rows = [_txn(transaction_id=1), _txn(transaction_id=2), _txn(transaction_id=3)]
    out = fmt.transactions_table(rows)
    assert out.count("<tr id=") == 3
    assert "<thead>" in out


def test_alert_escapes_and_tags_kind():
    out = fmt.alert("<b>boom</b>", kind="error")
    assert 'class="alert alert-error"' in out
    assert "<b>boom</b>" not in out
    assert "&lt;b&gt;boom" in out


def test_ai_panel_escapes_text():
    out = fmt.ai_panel("2 < 3 & 4 > 1")
    assert "&lt; 3 &amp; 4 &gt;" in out
