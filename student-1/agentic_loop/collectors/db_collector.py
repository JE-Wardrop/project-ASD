import sqlite3
from pathlib import Path
import requests
import os

#might have to chnage this to match the database location
DATABASE_NAME = "cm.db"
REQUIRED_FIELDS = {"card_id", "card_holder_name", "card_number", "card_type", "expiry_date", "status", "credit_limit"}
VALID_STATUSES = {"Freezed", "UnFreezed"}


#have to make this match the database schema


def _validate_card(card: dict) -> tuple[bool, str]:
    missing = REQUIRED_FIELDS - card.keys()
    
    if missing:
        return False, f"card missing field(s): {', '.join(sorted(missing))}"
    if not isinstance(card["card_id"], int):
        return False, "card_id must be integer"
    if not card["card_holder_name"]:
        return False, "card_holder_name required"
    if not card["card_number"]:
        return False, "card_number required"
    if card["status"] not in VALID_STATUSES:
        return False, f"status must be one of {', '.join(sorted(VALID_STATUSES))}"
    return True, "ok"


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    """Collect database evidence by querying the live database-service."""
    database_service_url = os.getenv("DATABASE_SERVICE_URL", "http://localhost:5002")

    try:
        response = requests.get(f"{database_service_url}/cards", timeout=5)
    except requests.exceptions.ConnectionError:
        return False, "database-service not reachable. Start docker-compose first."
    except requests.exceptions.Timeout:
        return False, "database-service request timed out."

    if response.status_code != 200:
        return False, f"database-service returned status {response.status_code}"

    cards = response.json()

    if len(cards) != 10:
        return False, f"Expected 10 cards, found {len(cards)}"

    for card in cards:
        ok, msg = _validate_card(card)
        if not ok:
            return False, msg

    count_active = sum(1 for c in cards if c["status"] == "Active")
    count_visa = sum(1 for c in cards if c["card_type"].lower() == "visa")

    return True, (
        "Database evidence: cards table has 10 valid rows; "
        f"Active status count is {count_active}; Visa card count is {count_visa}; "
        "fields are card_id, card_holder_name, card_number, card_type, expiry_date, status, credit_limit."
    )




# def _validate_student(student: tuple[int, str, str]) -> tuple[bool, str]:
#     student_id, student_name, subject_code = student
#     if not isinstance(student_id, int):
#         return False, "student_id must be integer"
#     if not student_name:
#         return False, "student_name required"
#     if not subject_code:
#         return False, "subject_code required"
#     return True, "ok"


# def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
#     db_path = app_dir / "legacy-lab3" / DATABASE_NAME
#     if not db_path.exists():
#         return False, f"Missing local database file: {db_path.name}"

#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     students = cursor.execute(
#         """
#         SELECT student_id, student_name, subject_code
#         FROM students
#         """
#     ).fetchall()
#     count_asd101 = cursor.execute(
#         "SELECT COUNT(*) FROM students WHERE subject_code = ?",
#         ("ASD101",),
#     ).fetchone()[0]
#     conn.close()

#     if len(students) != 10:
#         return False, f"Expected 10 students, found {len(students)}"

#     for student in students:
#         ok, msg = _validate_student(student)
#         if not ok:
#             return False, msg

#     return True, (
#         "Database evidence: students table has 10 valid rows; "
#         f"ASD101 rows count is {count_asd101}; fields are student_id, student_name, subject_code."
#     )