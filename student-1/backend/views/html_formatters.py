def format_cards_html(cards):
    if not cards:
        return "<p>No cards found.</p>"

    html = "<ul>"
    for card in cards:
        html += (
            f"<li>#{card['card_id']} - {card['card_holder_name']} - "
        )
    html += "</ul>"
    return html


def format_card_html(card):
    return (
        f"<p>ID: {card['card_id']}<br>"
        f"Holder: {card['card_holder_name']}<br>"
        f"Card Number: {card['card_number']}<br>"
    )
