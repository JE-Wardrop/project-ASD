from flask import Blueprint, request
import requests 

from services.database_api import (
    create_card_response,
    delete_card_response,
    get_card_by_id_response,
    get_cards,
    get_cards_by_status_response,
    get_cards_by_type_response,
    update_card_response,
)
from views.html_formatters import format_card_html, format_cards_html

normal_mode_bp = Blueprint("normal_mode", __name__)


@normal_mode_bp.get("/")
def health():
    return "<p>card-service running</p>", 200


@normal_mode_bp.get("/cards")
def get_cards_route():
    try:
        return format_cards_html(get_cards()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve cards from database-service.</p>"
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
            "<p>Failed to retrieve card from database-service.</p>"
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
            "<p>Failed to retrieve card-type results from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_mode_bp.get("/cards/by-status")
def get_cards_by_status():
    status = request.args.get("status", "").strip()

    if not status:
        return "<p>Status is required.</p>", 400

    try:
        response = get_cards_by_status_response(status)

        if response.status_code == 404:
            return f"<p>No cards found with status {status}.</p>", 404

        response.raise_for_status()
        return format_cards_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve status results from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_mode_bp.post("/cards/create")
def create_card():
    payload = {
        "card_holder_name": request.form.get("card_holder_name", "").strip(),
        "card_number": request.form.get("card_number", "").strip(),
        "card_type": request.form.get("card_type", "").strip(),
        "expiry_date": request.form.get("expiry_date", "").strip(),
        "status": request.form.get("status", "").strip(),
        "credit_limit": request.form.get("credit_limit", "").strip(),
    }

    try:
        response = create_card_response(payload)

        if response.status_code == 400:
            return f"<p>{response.json().get('error', 'Invalid card data.')}</p>", 400

        response.raise_for_status()
        return format_card_html(response.json()), 201
    except requests.RequestException as exc:
        return (
            "<p>Failed to create card in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_mode_bp.post("/cards/update")
def update_card():
    card_id = request.form.get("card_id", "").strip()

    if not card_id:
        return "<p>Card ID is required.</p>", 400

    payload = {}
    for field in ("card_holder_name", "card_number", "card_type", "expiry_date", "status", "credit_limit"):
        value = request.form.get(field, "").strip()
        if value:
            payload[field] = value

    try:
        responsnormal_ui_bpe = update_card_response(card_id, payload)

        if response.status_code == 404:
            return "<p>Card not found.</p>", 404
        if response.status_code == 400:
            return f"<p>{response.json().get('error', 'Invalid update.')}</p>", 400

        response.raise_for_status()
        return format_card_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to update card in database-service.</p>"
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
            "<p>Failed to delete card in database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )