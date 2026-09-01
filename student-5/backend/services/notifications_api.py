import os

import requests


NOTIFICATIONS_URL = os.environ.get("NOTIFICATIONS_URL", "http://localhost:8203")
TIMEOUT = 5


def send(user_id, message, notification_type="TRANSACTION"):
    if user_id is None:
        return False
    try:
        # call Notifications service to send notification
        resp = requests.post(
            f"{NOTIFICATIONS_URL}/notifications",
            json={
                "user_id": user_id,
                "notification_type": notification_type,
                "message": message,
                "status": "UNREAD",
            },
            timeout=TIMEOUT,
        )
        return resp.status_code < 400
    except requests.RequestException as exc:
        print("Could not send notification: %s", exc)
        return False