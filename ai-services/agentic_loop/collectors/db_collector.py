# OBSERVE: gather real evidence about the target's database microservice.

# Nothing here is specific to one feature. It checks what the specification
# requires of every student: an owned schema, at least ten seeded records,
# and a database service that answers /health.

# might have to change this a little to make it so that it can work with
# other forms of databases.


import re
import sqlite3
from pathlib import Path

import requests

MIN_SEED_ROWS = 10          # required by the project specification


def _load_schema_in_memory(schema_sql: str, seed_sql: str) -> tuple[dict[str, int], str | None]:
    """Run schema.sql and seed.sql against an in-memory database.

    This proves the SQL actually works, and gives a real row count per table
    without touching the developer's own database file.
    """
    try:
        connection = sqlite3.connect(":memory:")
        connection.executescript(schema_sql)
        connection.executescript(seed_sql)
    except sqlite3.Error as exc:
        return {}, f"SQL failed to execute: {exc}"

    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    ]
    counts = {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }
    connection.close()
    return counts, None

# This will load the prompts for if the model is a schema model
# I may get rid of this later but the purpose of this will be to load 
# different prompts for the other db sturctures
def _is_schema_model():
    pass


def collect(target, repo_root: Path) -> tuple[bool, str]:

    # I updated this code so that the db_collecter will still run on other student's code. 
    # The prompts still need to be updated though bc they still are excpeting:
    # schema.sql and seed.sql (and therefore is saying that code doesn't meet requirements)

    database_dir = target.root / "database"
    schema_path = database_dir / "schema.sql"
    seed_path = database_dir / "seed.sql"

    findings: list[str] = []


    hasSchema = [p.name for p in (schema_path, seed_path) if not p.exists()]
    if hasSchema:
        #run _is_schema_model()

        if _is_schema_model() == False:
            return False, f"{target.key}: missing {', '.join(hasSchema)} in database/"
        else:
            return True, f"Database evidence for {target.key} ({target.label}): " + "; ".join(findings) + "."

        
    # This will be if the agentic_loop is not missing schema data (uses schema data)
    else: 
        schema_sql = schema_path.read_text(encoding="utf-8")
        seed_sql = seed_path.read_text(encoding="utf-8")

        check_constraints = len(re.findall(r"\bCHECK\s*\(", schema_sql, re.IGNORECASE))
        findings.append(f"schema.sql defines {check_constraints} CHECK constraint(s)")


        counts, error = _load_schema_in_memory(schema_sql, seed_sql)
        if error:
            return False, f"{target.key}: {error}"

        for table, count in counts.items():
            state = "meets" if count >= MIN_SEED_ROWS else "BELOW"
            findings.append(f"table '{table}' seeded with {count} rows ({state} the minimum of {MIN_SEED_ROWS})")

        try:
            response = requests.get(f"{target.database_url}/health", timeout=3)
            findings.append(
                f"database service on port {target.database_port} "
                f"returned {response.status_code} for /health"
            )
        except requests.RequestException:
            findings.append(
                f"database service on port {target.database_port} is not running "
                "(file evidence only)"
            )

        return True, f"Database evidence for {target.key} ({target.label}): " + "; ".join(findings) + "."