DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    transaction_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_account_id    INTEGER,          -- NULL khi DEPOSIT  (tien tu ngoai vao)
    receiver_account_id  INTEGER,          -- NULL khi WITHDRAWAL (tien ra ngoai)

    transaction_type     TEXT    NOT NULL
        CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER')),

    -- Luon la so duong. Chieu tien suy ra tu transaction_type,
    -- khong bao gio luu so am.
    amount               REAL    NOT NULL CHECK (amount > 0),

    currency             TEXT    NOT NULL DEFAULT 'AUD',

    -- PENDING   : vua tao, chua cham vao balance
    -- COMPLETED : balance ben Accounts da cap nhat xong
    -- FAILED    : khong du tien / account bi freeze / Accounts service loi
    -- CANCELLED : nguoi dung huy (DELETE = soft delete)
    status               TEXT    NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED')),

    description          TEXT,

    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Rang buoc theo loai giao dich: dam bao du lieu khong bao gio vo nghia
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

-- Index cho cac truy van thuong dung nhat cua frontend:
-- lich su theo tai khoan, va bo loc theo type/status.
CREATE INDEX idx_txn_sender    ON transactions (sender_account_id);
CREATE INDEX idx_txn_receiver  ON transactions (receiver_account_id);
CREATE INDEX idx_txn_type      ON transactions (transaction_type);
CREATE INDEX idx_txn_status    ON transactions (status);
CREATE INDEX idx_txn_created   ON transactions (created_at DESC);

-- Tu dong cap nhat updated_at moi khi co UPDATE
CREATE TRIGGER trg_txn_updated_at
AFTER UPDATE ON transactions
FOR EACH ROW
BEGIN
    UPDATE transactions
       SET updated_at = datetime('now')
     WHERE transaction_id = OLD.transaction_id;
END;
