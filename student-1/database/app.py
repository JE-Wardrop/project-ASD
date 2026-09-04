# from pickle import GET

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'cm.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# # debug
# def get_db_connection():
#     conn = sqlite3.connect('cm.db')
#     conn.row_factory = sqlite3.Row 
#     return conn



@app.get("/")
def health():

    #debug
    conn = get_db_connection()
    cards = conn.execute('SELECT * FROM cards').fetchall()
    conn.close()
    return jsonify([dict(card) for card in cards]), 200, jsonify({"service": "database", "status": "running"})
    
    #normal
    # return jsonify({"service": "database", "status": "running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)