from flask import Flask, render_template, request, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import sqlite3
import os

from pathlib import Path
from flask_cors import CORS


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


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(normal_mode_bp)
    app.register_blueprint(ai_mode_bp)
    
    print("blueprints are running.")

    return app

app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
