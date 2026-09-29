Transaction Management handles three transaction types: DEPOSIT, WITHDRAWAL and TRANSFER. All amounts are in Australian dollars (AUD) and must be positive; the direction of money comes from the transaction type, not the sign of the amount.

A DEPOSIT has a receiver account only. A WITHDRAWAL has a sender account only. A TRANSFER needs both a sender and a receiver account, and the two accounts must be different.

A transaction has one of four statuses: PENDING, COMPLETED, FAILED or CANCELLED. COMPLETED means the money moved. FAILED means it was rejected, for example because of insufficient funds or a closed or frozen receiver account. PENDING means it is still waiting, for example for account verification.

Cancelling a transaction is a soft delete by default: its status changes to CANCELLED and the record is kept for the audit trail. A COMPLETED transaction cannot be cancelled. The database API also supports a permanent hard delete when explicitly requested.

A transfer adjusts both account balances through the Accounts service balance endpoint. If the Accounts service rejects the balance change, the transaction is marked FAILED.
