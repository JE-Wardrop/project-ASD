import json
import sqlite3
from datetime import datetime 
from database.init_db import DATABASE_NAME



def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_card(card_number, account_holder, card_type, expiry_date):
    card = {card_number, account_holder, card_type, expiry_date}
    conn = get_db_connection()
    cursor = conn.cursor()

    
    cursor.execute("INSERT INTO cards (card_number, account_holder, card_type, expiry_date) VALUES (?, ?, ?, ?)", 
                   (card_number, account_holder, card_type, expiry_date))
    conn.commit()
    conn.close()


def read_card(card_number, account_holder, card_type, expiry_date):
    pass


def update_card(card_number, account_holder, card_type, expiry_date):
    pass


def delete_card(card_number, account_holder, card_type, expiry_date):
    pass


def freeze_card (card_number, account_holder, card_type, expiry_date):
    pass

def unfreeze_card (card_number, account_holder, card_type, expiry_date):
    pass