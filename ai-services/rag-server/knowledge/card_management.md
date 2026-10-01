Card Management allows for users to access the database of cardholders. They much search for cards based off their own card_id and user_id.

Each card in the database is formatted as (card_id, user_id, card number, card type, expiry, status, balance).

Cards have different statuses: FROZEN and UNFROZEN. These can be changed at anytime.

Cards have 2 different types Credit and Debit. 

User's have the ability to:
- Create cards with their user_id
- Get (search for) cards based off their card_id
- Delete a card based off card_id
- Update a card's details (Credit or Debit) based off card_id
- Freeze card based on card_id
- Unfreeze card based on card_id

Users are formatted (user_id, name, email, password, address, phone number). Users need to use their user_ID to search for there cards and make changes  to their cards. 