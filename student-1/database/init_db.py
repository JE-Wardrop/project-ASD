import sqlite3

DATABASE_NAME = "cm.db"
users = [
    ("John Smith", "john.smith@example.com", "password123", "123 Main St, Anytown, USA", "555-1234")
]
cards = [
    (1, "1234567890123456", "Debit", "2025-12-31", "Unfrozen"),
    (1, "4567890123456789", "Credit", "2025-12-31", "Frozen"),
]

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
    "INSERT INTO users (name, email, password, address, phone) VALUES (?, ?, ?, ?, ?)",
    users
)

cursor.executemany(
    "INSERT INTO cards (user_id, card_number, card_type, expiry_date, status) VALUES (?, ?, ?, ?, ?)",
    cards
)

conn.commit()
conn.close()

print("database initalised with example")