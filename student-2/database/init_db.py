import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "accounts.db"))

VALID_ACCOUNT_TYPES = ("EVERYDAY", "SAVINGS")
VALID_STATUSES = ("ACTIVE", "FROZEN", "CLOSED")

# (user_id, account_number, account_type, balance, account_status, created_at)
accounts = [
    (1, "10000001", "EVERYDAY", 2540.50, "ACTIVE", "2026-01-05 09:00:00"),
    (1, "10000002", "SAVINGS", 8120.00, "ACTIVE", "2026-01-05 09:05:00"),
    (2, "10000003", "EVERYDAY", 315.20, "ACTIVE", "2026-01-08 11:30:00"),
    (3, "10000004", "SAVINGS", 15230.75, "ACTIVE", "2026-01-10 14:12:00"),
    (4, "10000005", "EVERYDAY", 90.00, "FROZEN", "2026-01-12 08:45:00"),
    (5, "10000006", "EVERYDAY", 4500.00, "ACTIVE", "2026-01-15 16:20:00"),
    (5, "10000007", "SAVINGS", 22000.00, "ACTIVE", "2026-01-15 16:25:00"),
    (6, "10000008", "EVERYDAY", 0.00, "CLOSED", "2026-01-18 10:00:00"),
    (7, "10000009", "SAVINGS", 1200.30, "ACTIVE", "2026-01-20 13:40:00"),
    (8, "10000010", "EVERYDAY", 675.45, "ACTIVE", "2026-01-22 17:05:00"),
]


def init_db():
    os.makedirs(os.path.dirname(DATABASE_NAME) or ".", exist_ok=True)

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_number TEXT NOT NULL UNIQUE,
            account_type TEXT NOT NULL CHECK(account_type IN {VALID_ACCOUNT_TYPES}),
            balance REAL NOT NULL DEFAULT 0.0,
            account_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(account_status IN {VALID_STATUSES}),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("DELETE FROM accounts")
    # Reset the AUTOINCREMENT counter so re-seeding (e.g. Flask's debug
    # reloader re-running this on startup) always yields account_id 1..N
    # instead of drifting upward on every restart.
    cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'accounts'")

    cursor.executemany(
        """
        INSERT INTO accounts
            (user_id, account_number, account_type, balance, account_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        accounts,
    )

    conn.commit()
    conn.close()

    print(f"Database initialized with {len(accounts)} accounts.")


if __name__ == "__main__":
    init_db()
