# from pickle import GET

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)

DATABASE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cm.db")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)