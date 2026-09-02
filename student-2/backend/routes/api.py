import requests
from flask import Blueprint, jsonify

from services import database_api as db

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    try:
        db_ok = requests.get(f"{db.DATABASE_SERVICE_URL}/", timeout=db.TIMEOUT).ok
    except requests.RequestException:
        db_ok = False

    return (
        jsonify(
            {
                "service": "student2-backend",
                "status": "ok" if db_ok else "degraded",
                "database": "ok" if db_ok else "unreachable",
            }
        ),
        200 if db_ok else 503,
    )


@api_bp.get("/accounts/<int:account_id>/balance")
def account_balance(account_id):
    try:
        resp = db.get_account_balance_response(account_id)
    except requests.RequestException as exc:
        return jsonify({"error": "database-service unreachable", "detail": str(exc)}), 503

    if resp.status_code == 404:
        return jsonify({"error": "Account not found"}), 404
    try:
        return jsonify(resp.json()), resp.status_code
    except ValueError:
        return jsonify({"error": "database-service returned invalid data"}), 502
