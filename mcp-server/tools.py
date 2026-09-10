import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent
DATABASE_PATH = APP_DIR / "enrolment.db"


def _connect_db():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_card_count():
    conn = _connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS card_count FROM cards")
        row = cursor.fetchone()
        return {"card_count": row[0] if row else 0}
    finally:
        conn.close()


# def get_students_by_subject(subject_code: str):
#     subject = (subject_code or "").strip().upper()
#     if not subject:
#         return {"error": "subject_code is required"}

#     conn = _connect_db()
#     try:
#         cursor = conn.cursor()
#         cursor.execute(
#             """
#             SELECT student_id, student_name, subject_code
#             FROM students
#             WHERE subject_code = ?
#             ORDER BY student_id
#             """,
#             (subject,),
#         )
#         return [dict(row) for row in cursor.fetchall()]
#     finally:
#         conn.close()


def list_project_files(directory_path: str = ".."):  # relative to mcp-server/
    path = (BASE_DIR / directory_path).resolve()
    if not path.exists() or not path.is_dir():
        return {"error": f"Directory not found: {path}"}

    return sorted(item.name for item in path.iterdir())


def read_ci_report(report_path: str = "../reports/report.json"):
    report_file = (BASE_DIR / report_path).resolve()
    if not report_file.exists():
        return {
            "error": "Report not found",
            "path": str(report_file),
            "hint": "Run Lab 05 workflow_dispatch to generate report.json",
        }

    with report_file.open("r", encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    print(get_card_count())
    # print(get_students_by_subject("ASD101"))
    print(list_project_files(".."))
    print(read_ci_report("../reports/report.json"))