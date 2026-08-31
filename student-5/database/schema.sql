DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    transaction_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_account_id    INTEGER,          -- NULL for DEPOSIT  (money coming in from outside)
    receiver_account_id  INTEGER,          -- NULL for WITHDRAWAL (money going out)

    transaction_type     TEXT    NOT NULL
        CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER')),

    -- Always a positive number. The direction of money is derived from
    -- transaction_type; a negative amount is never stored.
    amount               REAL    NOT NULL CHECK (amount > 0),

    currency             TEXT    NOT NULL DEFAULT 'AUD',

    -- PENDING   : just created, balance not touched yet
    -- COMPLETED : balance on the Accounts side has been updated
    -- FAILED    : insufficient funds / account frozen / Accounts service error
    -- CANCELLED : cancelled by the user (DELETE = soft delete)
    status               TEXT    NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED')),

    description          TEXT,

    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Constraint by transaction type: ensures the data is never meaningless
    CHECK (
        (transaction_type = 'DEPOSIT'
             AND sender_account_id IS NULL
             AND receiver_account_id IS NOT NULL)
     OR (transaction_type = 'WITHDRAWAL'
             AND sender_account_id IS NOT NULL
             AND receiver_account_id IS NULL)
     OR (transaction_type = 'TRANSFER'
             AND sender_account_id IS NOT NULL
             AND receiver_account_id IS NOT NULL
             AND sender_account_id <> receiver_account_id)
    )
);

-- Indexes for the frontend's most common queries:
-- history by account, and filtering by type/status.
CREATE INDEX idx_txn_sender    ON transactions (sender_account_id);
CREATE INDEX idx_txn_receiver  ON transactions (receiver_account_id);
CREATE INDEX idx_txn_type      ON transactions (transaction_type);
CREATE INDEX idx_txn_status    ON transactions (status);
CREATE INDEX idx_txn_created   ON transactions (created_at DESC);

-- Automatically update updated_at on every UPDATE
CREATE TRIGGER trg_txn_updated_at
AFTER UPDATE ON transactions
FOR EACH ROW
BEGIN
    UPDATE transactions
       SET updated_at = datetime('now')
     WHERE transaction_id = OLD.transaction_id;
END;
