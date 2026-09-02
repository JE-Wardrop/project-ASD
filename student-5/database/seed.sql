
-- Account IDs below map to the Accounts service (student-2) account_id (PK 1..10):
--   id 1  user 1  10000001  EVERYDAY  ACTIVE
--   id 2  user 1  10000002  SAVINGS   ACTIVE
--   id 3  user 2  10000003  EVERYDAY  ACTIVE
--   id 4  user 3  10000004  SAVINGS   ACTIVE
--   id 5  user 4  10000005  EVERYDAY  FROZEN   -> only used for FAILED / CANCELLED
--   id 6  user 5  10000006  EVERYDAY  ACTIVE
--   id 7  user 5  10000007  SAVINGS   ACTIVE
--   id 8  user 6  10000008  EVERYDAY  CLOSED   -> only used for FAILED / CANCELLED
--   id 9  user 7  10000009  SAVINGS   ACTIVE
--   id 10 user 8  10000010  EVERYDAY  ACTIVE

INSERT INTO transactions
    (sender_account_id, receiver_account_id, transaction_type, amount, currency, status, description, created_at)
VALUES
    -- ---------- DEPOSIT (sender NULL) ----------
    (NULL, 1, 'DEPOSIT',    2500.00, 'AUD', 'COMPLETED', 'Salary deposit - August',        '2026-08-01 09:15:00'),
    (NULL, 3, 'DEPOSIT',     850.50, 'AUD', 'COMPLETED', 'Cash deposit at branch',         '2026-08-03 14:22:00'),
    (NULL, 4, 'DEPOSIT',    1200.00, 'AUD', 'COMPLETED', 'Refund from insurance claim',    '2026-08-05 11:40:00'),
    (NULL, 1, 'DEPOSIT',     300.00, 'AUD', 'PENDING',   'Cheque deposit - clearing',      '2026-08-28 16:05:00'),

    -- ---------- WITHDRAWAL (receiver NULL) ----------
    (1, NULL, 'WITHDRAWAL',  200.00, 'AUD', 'COMPLETED', 'ATM withdrawal - Central Station','2026-08-06 18:30:00'),
    (3, NULL, 'WITHDRAWAL',  120.75, 'AUD', 'COMPLETED', 'EFTPOS - Woolworths Broadway',   '2026-08-08 12:10:00'),
    (9, NULL, 'WITHDRAWAL', 5000.00, 'AUD', 'FAILED',    'Insufficient funds',             '2026-08-10 08:45:00'),
    (5, NULL, 'WITHDRAWAL',   80.00, 'AUD', 'CANCELLED', 'Cancelled by customer',          '2026-08-12 19:55:00'),

    -- ---------- TRANSFER (both accounts set) ----------
    (1, 2, 'TRANSFER',    450.00, 'AUD', 'COMPLETED', 'Rent share - August',            '2026-08-14 10:00:00'),
    (3, 4, 'TRANSFER',     75.25, 'AUD', 'COMPLETED', 'Dinner split',                   '2026-08-16 20:18:00'),
    (6, 7, 'TRANSFER',   1500.00, 'AUD', 'COMPLETED', 'Savings top-up',                 '2026-08-18 13:33:00'),
    (10, 9, 'TRANSFER',    220.00, 'AUD', 'PENDING',   'Awaiting account verification',  '2026-08-27 09:02:00'),
    (7, 8, 'TRANSFER',   3200.00, 'AUD', 'FAILED',    'Receiver account closed',        '2026-08-25 15:47:00'),
    (2, 5, 'TRANSFER',     60.00, 'AUD', 'CANCELLED', 'Receiver account frozen',        '2026-08-26 17:21:00');
