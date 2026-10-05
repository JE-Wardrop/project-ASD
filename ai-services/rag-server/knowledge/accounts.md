Bank Account Management stores one record per customer bank account. Each account belongs to one user (user_id), and a user may own several accounts. Every account has a unique 8-digit account number, an account type, a balance in Australian dollars (AUD) and an account status.

There are two account types: EVERYDAY for day-to-day spending and SAVINGS for money set aside. A new account is always created with status ACTIVE. The balance can start at zero but can never become negative.

An account has one of three statuses: ACTIVE, FROZEN or CLOSED. An ACTIVE account can be frozen. A FROZEN account can be unfrozen, which returns it to ACTIVE. Both ACTIVE and FROZEN accounts can be closed. CLOSED is final: a closed account cannot be unfrozen or reopened.

Only an ACTIVE account can have its balance changed. A FROZEN or CLOSED account rejects every balance change, so it cannot receive a deposit, make a withdrawal, or send or receive a transfer. A balance change that would make the balance negative is rejected with insufficient funds.

The Transactions service changes balances through the Accounts balance adjustment endpoint. When that endpoint rejects the change because the account is frozen, closed or has insufficient funds, the transaction is marked FAILED.

Updating an account can only change its account number or account type. The status changes only through the freeze, unfreeze and close actions, and the balance changes only through the balance adjustment endpoint.
