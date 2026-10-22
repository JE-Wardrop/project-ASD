def format_cards_html(cards):
    if not cards:
        return "<p>No cards found.</p>"

    html = "<ul>"
    for card in cards:
        html += (
            f"<li>#{card['card_id']} - {card['card_number']} - "
            f"{card['card_type']} - {card['status']} (user {card['user_id']})</li>"
        )
    html += "</ul>"
    return html


def format_card_html(card):
    return (
        f"<p>Card ID: {card['card_id']}<br>"
        f"Card Number: {card['card_number']}<br>"
        f"Status: {card['status']}<br>"
        f"Type: {card['card_type']}<br>"
        # f"Expiry: {card['expiry']}<br>"
        # f"User Associated: {card['user_id']}<br>"
    )
