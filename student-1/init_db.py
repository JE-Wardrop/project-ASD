import sqlite3

DATABASE_NAME = "cm.db"

#card number, name, card type, expiry date

cards = [
    ("1234567890123456", "John Smith", "Debit", "2025-12-31"),
    ("2345678901234567", "Sarah Jones", "Credit", "2024-12-31"),
    ("3456789012345678", "Michael Lee", "Debit", "2023-12-31"),
    ("4567890123456789", "Emma Brown", "Credit", "2026-12-31"),
    ("5678901234567890", "James Wilson", "Debit", "2025-12-31"),
    ("6789012345678901", "Olivia White", "Credit", "2024-12-31"),
    ("7890123456789012", "Daniel Green", "Debit", "2023-12-31"),
    ("8901234567890123", "Sophia Hall", "Credit", "2026-12-31"),
    ("9012345678901234", "Liam King", "Debit", "2025-12-31"),
    ("0123456789012345", "Chloe Young", "Credit", "2024-12-31")
]

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()


cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards (
        card_id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_number TEXT UNIQUE NOT NULL,
        account_holder TEXT NOT NULL,
        card_type TEXT CHECK(card_type IN ('Debit', 'Credit')) NOT NULL,
        expiry_date TEXT NOT NULL,
        status TEXT CHECK(status IN ('Active', 'Blocked', 'Expired')) DEFAULT 'Active',
        balance REAL DEFAULT 0.0
    )
''')

cursor.execute("DELETE FROM cards")

cursor.executemany(
    "INSERT INTO cards (card_number, account_holder, card_type, expiry_date) VALUES (?, ?, ?, ?)",
    cards
)

conn.commit()
conn.close()

print("Database initialized with 10 cards.")