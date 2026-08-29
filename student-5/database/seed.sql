-- ============================================================
-- Student 5 — Transaction Management
-- Du lieu mau. Spec yeu cau toi thieu 10 ban ghi; o day co 14
-- de phu du 3 transaction_type va ca 4 gia tri status.
--
-- LUU Y: account_id 1001-1006 phai KHOP voi seed data cua
-- student-2 (Bank Account Management). Neu Binh dung day so
-- khac, sua lai o day truoc khi demo.
-- ============================================================

INSERT INTO transactions
    (sender_account_id, receiver_account_id, transaction_type, amount, currency, status, description, created_at)
VALUES
    -- ---------- DEPOSIT (sender NULL) ----------
    (NULL, 1001, 'DEPOSIT',    2500.00, 'AUD', 'COMPLETED', 'Salary deposit - August',        '2026-08-01 09:15:00'),
    (NULL, 1002, 'DEPOSIT',     850.50, 'AUD', 'COMPLETED', 'Cash deposit at branch',         '2026-08-03 14:22:00'),
    (NULL, 1003, 'DEPOSIT',    1200.00, 'AUD', 'COMPLETED', 'Refund from insurance claim',    '2026-08-05 11:40:00'),
    (NULL, 1001, 'DEPOSIT',     300.00, 'AUD', 'PENDING',   'Cheque deposit - clearing',      '2026-08-28 16:05:00'),

    -- ---------- WITHDRAWAL (receiver NULL) ----------
    (1001, NULL, 'WITHDRAWAL',  200.00, 'AUD', 'COMPLETED', 'ATM withdrawal - Central Station','2026-08-06 18:30:00'),
    (1002, NULL, 'WITHDRAWAL',  120.75, 'AUD', 'COMPLETED', 'EFTPOS - Woolworths Broadway',   '2026-08-08 12:10:00'),
    (1003, NULL, 'WITHDRAWAL', 5000.00, 'AUD', 'FAILED',    'Insufficient funds',             '2026-08-10 08:45:00'),
    (1004, NULL, 'WITHDRAWAL',   80.00, 'AUD', 'CANCELLED', 'Cancelled by customer',          '2026-08-12 19:55:00'),

    -- ---------- TRANSFER (ca hai account) ----------
    (1001, 1002, 'TRANSFER',    450.00, 'AUD', 'COMPLETED', 'Rent share - August',            '2026-08-14 10:00:00'),
    (1002, 1003, 'TRANSFER',     75.25, 'AUD', 'COMPLETED', 'Dinner split',                   '2026-08-16 20:18:00'),
    (1003, 1004, 'TRANSFER',   1500.00, 'AUD', 'COMPLETED', 'Car deposit payment',            '2026-08-18 13:33:00'),
    (1004, 1005, 'TRANSFER',    220.00, 'AUD', 'PENDING',   'Awaiting account verification',  '2026-08-27 09:02:00'),
    (1005, 1006, 'TRANSFER',   3200.00, 'AUD', 'FAILED',    'Receiver account frozen',        '2026-08-25 15:47:00'),
    (1006, 1001, 'TRANSFER',     60.00, 'AUD', 'CANCELLED', 'Cancelled before processing',    '2026-08-26 17:21:00');
