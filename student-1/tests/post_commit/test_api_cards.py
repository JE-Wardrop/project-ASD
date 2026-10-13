import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:8201")


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/", timeout=5)
    assert response.status_code == 200


def test_cards_exist():
    response = requests.get(f"{DATABASE_SERVICE_URL}/cards", timeout=5)
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) > 0


def test_card_by_id():
    response = requests.get(f"{DATABASE_SERVICE_URL}/cards/1", timeout=5)
    assert response.status_code == 200


def test_cards_by_status():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/cards/status",
        params={"status": "FROZEN"},
        timeout=5,
    )
    assert response.status_code == 200