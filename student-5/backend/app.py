import os
from flask import Flask
from flask_cors import CORS

from routes.normal_ui import bp as normal_ui_bp
from routes.ai_mode import ai_mode_bp
from services import database_api as db

SERVICE_NAME = "student5-backend"
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(normal_ui_bp)
    app.register_blueprint(ai_mode_bp)
    @app.get("/health")
    def health():
        try:
            db_ok = db.health().status_code == 200
        except Exception as exc:
            db_ok = False
        return ({"status": "ok" if db_ok else "degraded",
                 "service": SERVICE_NAME,
                 "database": "up" if db_ok else "down"},
                200 if db_ok else 503)
    
    @app.errorhandler(404)
    def not_found(_):
        return {"error": "Endpoint does not exist"}, 404
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)