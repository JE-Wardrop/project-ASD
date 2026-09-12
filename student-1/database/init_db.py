import sqlite3
import os

DATABASE_NAME = "cm.db"
users = [
    (1, "John Smith", "john.smith@example.com", "password123", "123 Main St, Anytown, AU", "0423456789"),
    (2, "Jane Doe", "jane.doe@example.com", "password456", "456 Oak Ave, Somewhere, AU", "04567891232"),
]
cards = [
    #(card_id, user_id, card number, card type, expiry, status, balance)
    (1, 1, "1234567890123456", "Debit", "2025-12-31", "Unfrozen", 0.0),
    (2, 1, "4567890123456789", "Credit", "2025-12-31", "Frozen", 0.0),
    (3, 1, "0987654321098765", "Debit", "2025-11-30", "Frozen", 0.0),
    (4, 1, "8901234567890123", "Credit", "2025-12-31", "Frozen", 0.0),
    (5, 2, "1234567890123455", "Debit", "2025-12-31", "Unfrozen", 0.0),
    (6, 2, "4567890123456788", "Credit", "2025-12-31", "Frozen", 0.0),
    (7, 2, "0987654321098769", "Debit", "2025-11-30", "Frozen", 0.0),
    (8, 2, "8901234567890120", "Credit", "2025-12-31", "Frozen", 0.0),
]


#debug
# if os.path.exists(DATABASE_NAME):
#     os.remove(DATABASE_NAME)
#     print(f"Removed old {DATABASE_NAME} file.")


conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()


# Should link to the users db
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        address TEXT,
        phone TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards (
        card_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        card_number TEXT UNIQUE NOT NULL,
        card_type TEXT CHECK(card_type IN ('Debit', 'Credit')) NOT NULL,
        expiry_date TEXT NOT NULL,
        status TEXT CHECK(status IN ('Unfrozen', 'Frozen')) DEFAULT 'Unfrozen',
        balance REAL DEFAULT 0.0,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
''')

cursor.executemany(
    "INSERT INTO users (user_id, name, email, password, address, phone) VALUES (?, ?, ?, ?, ?, ?)",
    users
)

cursor.executemany(
    "INSERT INTO cards (card_id, user_id, card_number, card_type, expiry_date, status, balance) VALUES (?, ?, ?, ?, ?, ?, ?)",
    cards
)

conn.commit()
conn.close()

print("database initialised with examples")
