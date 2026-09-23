import json
import sqlite3
from pathlib import Path


# Will have to be based off each student's database
# I don't know how to do this in an effcient way

BASE_DIR = Path(__file__).resolve().parent
AI_SERVICES_DIR = BASE_DIR.parent
STUDENT_LOCATION_PATHS = AI_SERVICES_DIR.parent

# you may have to reinitalise your database if you were having issues like I was lmao
DB_S1_PATH = STUDENT_LOCATION_PATHS / "student-1" / "database" / "cm.db"


# commented these out for now as they contain dummy data that will cause errors

# DB_S2_PATH = STUDENT_LOCATION_PATHS / "student-2" / "database" / "databasename.db"
# DB_S3_PATH = STUDENT_LOCATION_PATHS / "student-3" / "database" / "databasename.db"
# DB_S4_PATH = STUDENT_LOCATION_PATHS / "student-4" / "database" / "databasename.db"

# #student 5 will have to do this differently i think due to not having hte same set up
# DB_S5_PATH = STUDENT_LOCATION_PATHS / "student-5" / "database" / "databasename.db"


def _connect_db():
    if not DB_S1_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_S1_PATH}")

    # if not DB_S2_PATH.exists():
    #     raise FileNotFoundError(f"Database not found: {DB_S2_PATH}")

    # if not DB_S3_PATH.exists():
    #     raise FileNotFoundError(f"Database not found: {DB_S3_PATH}")

    # if not DB_S4_PATH.exists():
    #     raise FileNotFoundError(f"Database not found: {DB_S4_PATH}")

    # if not DB_S5_PATH.exists():
    #     raise FileNotFoundError(f"Database not found: {DB_S5_PATH}")

    
    conn = sqlite3.connect(DB_S1_PATH)

    # conn = sqlite3.connect(DB_S2_PATH)
    # conn = sqlite3.connect(DB_S3_PATH)
    # conn = sqlite3.connect(DB_S4_PATH)
    # conn = sqlite3.connect(DB_S5_PATH)

    conn.row_factory = sqlite3.Row
    return conn





# def health(){
#     
# }


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



# For each database

def debug_file_path():
    print(BASE_DIR)
    print(AI_SERVICES_DIR)
    print(STUDENT_LOCATION_PATHS)
    print(f"specific student:", DB_S1_PATH) 
    print(_connect_db())


def get_card_count():
    conn = _connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS card_count FROM cards")
        row = cursor.fetchone()
        return {"card_count": row[0] if row else 0}
    finally:
        conn.close()


def get_card_per_user():
    conn = _connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, card_id FROM cards" 
                       "")
        row = cursor.fetchone()
        return {"get_card_per_user": row[0] if row else 0}
    finally:
        conn.close()


if __name__ == "__main__":
    debug_file_path()
    print(get_card_count())
    print(get_card_per_user())
    print(list_project_files(".."))
    print(read_ci_report("../reports/report.json"))