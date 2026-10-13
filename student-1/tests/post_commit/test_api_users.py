import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:8201")


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/", timeout=5)
    assert response.status_code == 200


def test_users_exist():
    response = requests.get(f"{DATABASE_SERVICE_URL}/users", timeout=5)
    assert response.status_code == 200
    users = response.json()
    assert len(users) > 0
