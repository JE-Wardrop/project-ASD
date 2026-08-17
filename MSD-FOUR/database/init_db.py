import sqlite3

DATABASE_NAME = "users.db"

users = [
    (1, "john.smith", "john.smith@email.com", "John", "Smith", "0412345678"),
    (2, "sarah.jones", "sarah.jones@email.com", "Sarah", "Jones", "0423456789"),
    (3, "michael.lee", "michael.lee@email.com", "Michael", "Lee", "0434567890"),
    (4, "emma.brown", "emma.brown@email.com", "Emma", "Brown", "0445678901"),
    (5, "james.wilson", "james.wilson@email.com", "James", "Wilson", "0456789012"),
    (6, "olivia.white", "olivia.white@email.com", "Olivia", "White", "0467890123"),
    (7, "daniel.green", "daniel.green@email.com", "Daniel", "Green", "0478901234"),
    (8, "sophia.hall", "sophia.hall@email.com", "Sophia", "Hall", "0489012345"),
    (9, "liam.king", "liam.king@email.com", "Liam", "King", "0490123456"),
    (10, "chloe.young", "chloe.young@email.com", "Chloe", "Young", "0401234567")
]

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL
)
""")

cursor.execute("DELETE FROM users")

cursor.executemany(
    """
    INSERT INTO users
    (user_id, username, email, first_name, last_name, phone)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    users
)

conn.commit()
conn.close()

print("Database initialized with 10 users.")