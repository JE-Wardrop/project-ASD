import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:5002")


def get_cards():
    response = requests.get(f"{DATABASE_SERVICE_URL}/cards", timeout=5)
    response.raise_for_status()
    return response.json()


# def get_card_by_id_response(card_id):
#     return requests.get(f"{DATABASE_SERVICE_URL}/cards/{card_id}", timeout=5)


# def get_cards_by_type_response(card_type):
#     return requests.get(
#         f"{DATABASE_SERVICE_URL}/cards/by-type",
#         params={"card_type": card_type},
#         timeout=5,
#     )


# def get_cards_by_status_response(status):
#     return requests.get(
#         f"{DATABASE_SERVICE_URL}/cards/by-status",
#         params={"status": status},
#         timeout=5,
#     )


def create_card_response(payload):
    return requests.post(f"{DATABASE_SERVICE_URL}/cards", json=payload, timeout=5)


def update_card_response(card_id, payload):
    return requests.put(f"{DATABASE_SERVICE_URL}/cards/{card_id}", json=payload, timeout=5)


def delete_card_response(card_id):
    return requests.delete(f"{DATABASE_SERVICE_URL}/cards/{card_id}", timeout=5)