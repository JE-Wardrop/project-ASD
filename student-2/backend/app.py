import os
import sys
from pathlib import Path

from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from routes.ai_mode import ai_mode_bp
from routes.api import api_bp
from routes.auth_mode import auth_bp  # Lab 11: JWT token auth
from routes.mcp_mode import mcp_mode_bp
from routes.multi_agent_mode import multi_agent_mode_bp  # Lab 10: Multi-Agent tab
from routes.normal_ui import normal_ui_bp
from routes.rag_mode import rag_mode_bp


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(normal_ui_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ai_mode_bp)
    app.register_blueprint(mcp_mode_bp)
    app.register_blueprint(rag_mode_bp)
    app.register_blueprint(multi_agent_mode_bp)  # Lab 10: Multi-Agent tab
    app.register_blueprint(auth_bp)  # Lab 11: JWT token auth

    return app


app = create_app()


if __name__ == "__main__":
    # Lab 11 (Ruff S201): debug mode is opt-in through FLASK_DEBUG instead of always on.
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(
        host="0.0.0.0",  # noqa: S104 - container needs to bind all interfaces
        port=int(os.getenv("PORT", "5001")),
        debug=debug_mode,
    )
