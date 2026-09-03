import sqlite3
from pathlib import Path

DATABASE_NAME = Path(__file__).parent / "users.db"


users = [
    (1, "john.smith", "john.smith@email.com", "random_hash_001", "John", "Smith", "0412345678", "admin"),
    (2, "sarah.jones", "sarah.jones@email.com", "random_hash_002", "Sarah", "Jones", "0423456789", "client"),
    (3, "michael.lee", "michael.lee@email.com", "random_hash_003", "Michael", "Lee", "0434567890", "admin"),
    (4, "emma.brown", "emma.brown@email.com", "random_hash_004", "Emma", "Brown", "0445678901", "client"),
    (5, "james.wilson", "james.wilson@email.com", "random_hash_005", "James", "Wilson", "0456789012", "client"),
    (6, "olivia.white", "olivia.white@email.com", "random_hash_006", "Olivia", "White", "0467890123", "client"),
    (7, "daniel.green", "daniel.green@email.com", "random_hash_007", "Daniel", "Green", "0478901234", "client"),
    (8, "sophia.hall", "sophia.hall@email.com", "random_hash_008", "Sophia", "Hall", "0489012345", "client"),
    (9, "liam.king", "liam.king@email.com", "random_hash_009", "Liam", "King", "0490123456", "client"),
    (10, "chloe.young", "chloe.young@email.com", "random_hash_010", "Chloe", "Young", "0401234567", "client")
]
conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL

)
""")

cursor.execute("DELETE FROM users")

cursor.executemany(
    """
    INSERT INTO users
    (user_id, username, email, password, first_name, last_name, phone, role)
    VALUES (?, ?, ?,?, ?, ?, ?, ?)
    """,
    users
)

conn.commit()
conn.close()

print("Database initialized with 10 users.")