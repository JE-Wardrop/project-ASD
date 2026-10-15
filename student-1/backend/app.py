import os
import sqlite3

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from openai import OpenAI

load_dotenv()


DATABASE_NAME = "cm.db"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(BASE_DIR, "..", "frontend")
app = Flask(__name__, template_folder=template_dir)



client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)

from routes.ai_mode import ai_mode_bp
from routes.normal_mode import normal_mode_bp

from routes.auth_mode import auth_bp

try:
    from routes.mcp_mode import mcp_mode_bp
except Exception as e:
    print(f"mcp_mode failed to load: {e}")
    mcp_mode_bp = None

try:
    from routes.rag_mode import rag_mode_bp
except Exception as e:
    print(f"rag_mode failed to load: {e}")
    rag_mode_bp = None


try:
    from routes.multi_agent_mode import multi_agent_mode_bp
except Exception as e:
    print(f"multi_agent_mode failed to load: {e}")
    multi_agent_mode_bp = None




def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(normal_mode_bp)
    app.register_blueprint(ai_mode_bp)

    
    app.register_blueprint(auth_bp)


    if mcp_mode_bp:
        app.register_blueprint(mcp_mode_bp)
    if rag_mode_bp:
        app.register_blueprint(rag_mode_bp)
    if multi_agent_mode_bp:
        app.register_blueprint(multi_agent_mode_bp)

    print("blueprints are running.")

    return app

app = create_app()


if __name__ == "__main__":
    # Original Code (prior to lab 11) --------------------------------
    # app.run(host="0.0.0.0", port=5001, debug=True)

    # Code update from Lab 11 ----------------------------------------
    # Causing errors in test_ruff_scan_passes: Assesrtion error
    # This code will still allow the backend and workflow to work though :P

    # debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    # app.run(host="0.0.0.0", port=5001, debug=debug_mode)

    # Code for pre-commit testing ------------------------------------
    # Passes pre-commit tests
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    host_ip = os.getenv("FLASK_HOST", "127.0.0.1")
    port_num = int(os.getenv("PORT", "5001"))
    app.run(host=host_ip, port=port_num, debug=debug_mode)



