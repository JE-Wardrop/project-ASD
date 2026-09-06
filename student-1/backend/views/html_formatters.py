def format_cards_html(cards):
    if not cards:
        return "<p>No cards found.</p>"

    html = "<ul>"
    for card in cards:
        html += (
            f"<li>#{card['card_id']} - {card['card_name']} - "
        )
    html += "</ul>"
    return html


def format_card_html(card):
    return (
        f"<p>Card ID: {card['card_id']}<br>"
        f"Card Number: {card['card_number']}<br>"
        f"Status: {card['status']}<br>"
        # f"Expiry: {card['expiry']}<br>"
        # f"User Associated: {card['user_id']}<br>"
    )
