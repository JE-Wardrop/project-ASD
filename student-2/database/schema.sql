-- Mirrors the CREATE TABLE statement in database/init_db.py, which is what
-- actually runs against accounts.db at service startup. This file exists so
-- the shared agentic_loop DB review (ai-services/agentic_loop) can load and
-- validate the schema without touching the real database file. If you change
-- the schema in init_db.py, update this file to match.

DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    account_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    account_number  TEXT    NOT NULL UNIQUE,
    account_type    TEXT    NOT NULL
        CHECK (account_type IN ('EVERYDAY', 'SAVINGS')),
    balance         REAL    NOT NULL DEFAULT 0.0,
    account_status  TEXT    NOT NULL DEFAULT 'ACTIVE'
        CHECK (account_status IN ('ACTIVE', 'FROZEN', 'CLOSED')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
