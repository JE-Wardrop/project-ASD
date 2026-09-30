# Retrieval Metrics

## failed transactions (feature: transactions)
- Retrieved: ['transactions_13', 'transactions_7', 'transactions_12', 'transactions_4', 'transactions_11']
- Relevant: ['transactions_13', 'transactions_7']
- P@5: 0.4
- R@5: 1.0

## how many transactions are there (feature: transactions)
- Retrieved: ['transactions_8', 'transactions_13', 'transactions_11', 'transactions_2', 'transactions_10']
- Relevant: []
- P@5: 0.0
- R@5: 0.0

## can a completed transaction be cancelled (feature: transactions)
- Retrieved: ['transactions_5', 'transactions_14', 'transactions_2', 'transactions_8', 'transactions_10']
- Relevant: []
- P@5: 0.0
- R@5: 0.0

## frozen cards (feature: cards)
- Retrieved: ['cards_4', 'cards_6', 'cards_8', 'cards_2', 'cards_3']
- Relevant: ['cards_4', 'cards_6', 'cards_8', 'cards_2', 'cards_3']
- P@5: 1.0
- R@5: 1.0

## frozen accounts (feature: accounts)
- Retrieved: ['accounts_5', 'knowledge_accounts_2', 'knowledge_accounts_3', 'accounts_count', 'accounts_8']
- Relevant: ['accounts_5', 'knowledge_accounts_2']
- P@5: 0.4
- R@5: 1.0

## can a frozen account receive a deposit (feature: accounts)
- Retrieved: ['knowledge_accounts_2', 'accounts_5', 'knowledge_accounts_3', 'accounts_9', 'accounts_4']
- Relevant: ['knowledge_accounts_2']
- P@5: 0.2
- R@5: 1.0

## how many accounts are there (feature: accounts)
- Retrieved: ['accounts_3', 'accounts_8', 'accounts_4', 'accounts_9', 'accounts_count']
- Relevant: ['accounts_count']
- P@5: 0.2
- R@5: 1.0

## weather in Sydney (feature: all)
- Retrieved: []
- Relevant: []
- P@5: 1.0
- R@5: 1.0
