import sqlite3

DATABASE_NAME = "card_management_db.db"

card_information_parts = [
    (1, "John Smith", "ASD101"),
    (2, "Sarah Jones", "ASD101"),
]

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY NOT NULL UNIQUE,
        student_name TEXT NOT NULL,
        subject_code TEXT NOT NULL
    )
""")

cursor.execute("DELETE FROM students")

cursor.executemany(
    "INSERT INTO students (student_id, student_name, subject_code) VALUES (?, ?, ?)",
    card_information_parts
)

conn.commit()
conn.close()

print("Database initialized with 10 students.")