import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:8301")


def test_service_health_users():
    response = requests.get(f"{DATABASE_SERVICE_URL}/", timeout=5)
    assert response.status_code == 200


def test_users_exist():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/users",
        params={"users": "1"},
        timeout=5,
    )
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) > 0
