-- Mirrors the `accounts` seed list in database/init_db.py. Kept in sync
-- manually - if you add/change rows in init_db.py, update this file too.

INSERT INTO accounts
    (user_id, account_number, account_type, balance, account_status, created_at)
VALUES
    (1, '10000001', 'EVERYDAY',  2540.50, 'ACTIVE', '2026-01-05 09:00:00'),
    (1, '10000002', 'SAVINGS',   8120.00, 'ACTIVE', '2026-01-05 09:05:00'),
    (2, '10000003', 'EVERYDAY',   315.20, 'ACTIVE', '2026-01-08 11:30:00'),
    (3, '10000004', 'SAVINGS',  15230.75, 'ACTIVE', '2026-01-10 14:12:00'),
    (4, '10000005', 'EVERYDAY',    90.00, 'FROZEN', '2026-01-12 08:45:00'),
    (5, '10000006', 'EVERYDAY',  4500.00, 'ACTIVE', '2026-01-15 16:20:00'),
    (5, '10000007', 'SAVINGS',  22000.00, 'ACTIVE', '2026-01-15 16:25:00'),
    (6, '10000008', 'EVERYDAY',     0.00, 'CLOSED', '2026-01-18 10:00:00'),
    (7, '10000009', 'SAVINGS',   1200.30, 'ACTIVE', '2026-01-20 13:40:00'),
    (8, '10000010', 'EVERYDAY',   675.45, 'ACTIVE', '2026-01-22 17:05:00');
