from pickle import GET

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)

DATABASE_NAME = "/app/data/cm.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def health():
    return jsonify({"service": "database-service", "status": "running"})



@app.get("/add-card-details", methods=[GET, POST])
def add_card_details():
    if request.method == "POST":
        name = request.form.get("name")
        # Process the form data (e.g., save to database)
        return jsonify({"message": f"Card details for {name} added successfully!"})
    else:
        # Render the HTML form for GET requests
        return """
        <form method="POST">
            <label for="name">Enter Name:</label>
            <input type="text" id="name" name="name" required>
            <button type="submit">Submit</button>
        </form>
        """


# @app.get("/add-card-details" methods=["GET","POST"])
# def change_card_details():
#     pass


# @app.get("")
# def delete_card_details():
#     pass

# @app.get("")
# def freeze_state():
#     pass


@app.get("/cards")
def get_cards():
    conn = get_db_connection()
    cards = conn.execute(
        "SELECT card_id, user_id, card_number, card_type, expiry_date, status FROM cards"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in cards])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)