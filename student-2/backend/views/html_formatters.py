def format_accounts_html(accounts):
    if not accounts:
        return "<p>No accounts found.</p>"

    html = "<table><thead><tr>"
    html += (
        "<th>ID</th><th>User</th><th>Account #</th><th>Type</th>"
        "<th>Balance</th><th>Status</th><th>Created</th>"
    )
    html += "</tr></thead><tbody>"

    for account in accounts:
        html += (
            "<tr>"
            f"<td>{account['account_id']}</td>"
            f"<td>{account['user_id']}</td>"
            f"<td>{account['account_number']}</td>"
            f"<td>{account['account_type']}</td>"
            f"<td class=\"num\">${account['balance']:.2f}</td>"
            f"<td>{format_status_pill(account['account_status'])}</td>"
            f"<td>{account['created_at']}</td>"
            "</tr>"
        )

    html += "</tbody></table>"
    return html


def format_account_html(account):
    return (
        "<p>"
        f"Account ID: {account['account_id']}<br>"
        f"User ID: {account['user_id']}<br>"
        f"Account Number: {account['account_number']}<br>"
        f"Type: {account['account_type']}<br>"
        f"Balance: ${account['balance']:.2f}<br>"
        f"Status: {format_status_pill(account['account_status'])}<br>"
        f"Created: {account['created_at']}"
        "</p>"
    )


def format_balance_html(account):
    return (
        "<p>"
        f"Account ID: {account['account_id']}<br>"
        f"Balance: ${account['balance']:.2f}<br>"
        f"Status: {format_status_pill(account['account_status'])}"
        "</p>"
    )


def format_status_pill(status):
    pill_class = {
        "ACTIVE": "pill pill-ok",
        "FROZEN": "pill pill-wait",
        "CLOSED": "pill pill-bad",
    }.get(status, "pill pill-muted")

    return f'<span class="{pill_class}">{status}</span>'
