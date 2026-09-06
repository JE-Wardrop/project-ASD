from urllib import response

from flask import Blueprint, jsonify, request
import requests 
from flask_cors import CORS


from services.database_api import (
    create_card_response,
    delete_card_response,
    get_cards,
    update_card_response,
    get_card_by_id_response,
    get_cards_by_type_response,
    freeze_card_response,
    unfreeze_card_response,
)
from views.html_formatters import format_card_html, format_cards_html

normal_mode_bp = Blueprint("normal_mode", __name__)


@normal_mode_bp.get("/")
def health():
    return "<p>backend is running</p>", 200


@normal_mode_bp.get("/cards")
def get_cards_route():
    try:

        response = get_cards()
        return format_card_html(response.json()), response.status_code
    
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve cards from database</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_mode_bp.get("/cards/by-id")
def get_card_by_id():
    card_id = request.args.get("card_id", "").strip()

    if not card_id:
        return "<p>Card ID is required.</p>", 400

    try:
        response = get_card_by_id_response(card_id)

        if response.status_code == 404:
            return "<p>Card not found.</p>", 404
        if response.status_code == 400:
            return "<p>Card ID must be valid.</p>", 400

        response.raise_for_status()
        return format_card_html(response.json()), 200

    
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve card from database.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


    


@normal_mode_bp.get("/cards/by-type")
def get_cards_by_type():
    card_type = request.args.get("card_type", "").strip()

    if not card_type:
        return "<p>Card type is required.</p>", 400

    try:
        response = get_cards_by_type_response(card_type)

        if response.status_code == 404:
            return f"<p>No cards found for {card_type}.</p>", 404

        response.raise_for_status()
        return format_cards_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve card-type results from database.</p>"
            f"<pre>{exc}</pre>",
            503,
        )

# the backend cannot find the database's port or the route isn't functioning correctly. 

@normal_mode_bp.post("/cards/create")
def create_card():

    # What this function should do:
    # Create a card based upon the user's name and the card_type


    card_type = request.form.get("card_type", "").strip()
    card_id = request.form.get("card_id", "").strip()
    user_id = request.form.get("user_id", "").strip()

    if not all([card_type, user_id, card_id]):
        return "<p>All fields are required.</p>", 400

    payload = {
        "user_id": user_id,
        "card_id": card_id,
        "card_type": card_type,
        "card_number": "0000000000000000",
        "expiry_date": "2099-12-31",
        "status": "Unfrozen",
        "balance": 0.0,
    }

    try:

        # Changes will need to be made to this to make it work the way it is intended.

        response = create_card_response(payload)

        if response.status_code == 400:
            return f"<p>{response.json().get('error', 'Invalid card data.')}</p>", 400

        response.raise_for_status()
        return f"<p>Card created successfully</p>{format_card_html(response.json())}", 201

    except requests.RequestException as exc:
        return (
            "<p>Failed to create card in database</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_mode_bp.post("/cards/update")
def update_card():
    card_id = request.form.get("card_id", "").strip()

    if not card_id:
        return "<p>Card ID is required.</p>", 400

    payload = {}
    for field in ("user_id", "card_number", "card_type", "expiry_date", "status", "balance"):
        value = request.form.get(field, "").strip()
        if value:
            payload[field] = value

    try:
        response = update_card_response(card_id, payload)

        if response.status_code == 404:
            return "<p>Card not found.</p>", 404
        if response.status_code == 400:
            return f"<p>{response.json().get('error', 'Invalid update.')}</p>", 400

        response.raise_for_status()
        return format_card_html(response.json()), 200

    except requests.RequestException as exc:
        return (
            "<p>Failed to update card in database.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_mode_bp.post("/cards/delete")
def delete_card():
    card_id = request.form.get("card_id", "").strip()

    if not card_id:
        return "<p>Card ID is required.</p>", 400

    try:
        response = delete_card_response(card_id)

        if response.status_code == 404:
            return "<p>Card not found.</p>", 404

        response.raise_for_status()
        return f"<p>Card #{card_id} deleted.</p>", 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to delete card in database.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_mode_bp.post("/cards/freeze")
def freeze_card():
    card_number = request.form.get("card_number", "").strip()

    if not card_number:
        return "<p>Card number is required.</p>", 400

    try:
        response = freeze_card_response(card_number)

        if response.status_code == 404:
            return "<p>Card not found.</p>", 404
        if response.status_code == 400:
            return f"<p>{response.json().get('error', 'Invalid card number.')}</p>", 400

        response.raise_for_status()
        return format_card_html(response.json()), 200
    except requests.RequestException as exc:
        return "<p>Failed to freeze card in database.</p>" f"<pre>{exc}</pre>", 503


@normal_mode_bp.post("/cards/unfreeze")
def unfreeze_card():
    card_number = request.form.get("card_number", "").strip()

    if not card_number:
        return "<p>Card number is required.</p>", 400

    try:
        response = unfreeze_card_response(card_number)

        if response.status_code == 404:
            return "<p>Card not found.</p>", 404
        if response.status_code == 400:
            return f"<p>{response.json().get('error', 'Invalid card number.')}</p>", 400

        response.raise_for_status()
        return format_card_html(response.json()), 200
    except requests.RequestException as exc:
        return "<p>Failed to unfreeze card in database.</p>" f"<pre>{exc}</pre>", 503