# this app is currently defunked however I don't know if im meant to store app in backend or outside. 
# currently it is using the one outside 

# source .venv/bin/activate
# cd "/home/juno/Desktop/ASD 2026/project-ASD/student-1/backend"

# python3 -m venv .venv

from flask import Flask, render_template, request, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import sqlite3
import os
from pathlib import Path

load_dotenv()


DATABASE_NAME = "cm.db"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(BASE_DIR, "..", "frontend")
app = Flask(__name__, template_folder=template_dir)

#app = Flask(__name__, template_folder=template_dir, static_folder=template_dir)

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def home():
    return render_template('cm_main.html')

@app.route('/about')
def about_page():
    return render_template('cm_details.html')


@app.route('/ai_model', methods=['GET'])
def freeze_fet_card():
    return render_template('cm_freeze.html')


@app.route('/ai_model', methods=['GET'])
def render_ai_model():
    return render_template('cm_model.html')



@app.route('/ai_model', methods=['POST'])
def ai_model():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise software engineering assistant. "
                        "Answer in one short paragraph unless asked otherwise."
                    )
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            max_tokens=200,
            temperature=0.2,
        )

        answer = response.choices[0].message.content

        return f"<p>{answer}</p>"

    except Exception as exc:
        return (
            "<p>Local AI agent request failed. "
            "Check that Ollama is running and that qwen2.5:0.5b is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000,debug=True)