# from pickle import GET

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)


@app.get("/")
def health():
    return jsonify({"service": "database", "status": "running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)