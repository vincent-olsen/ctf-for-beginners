# noter5-backend

This is infrastructure for [noter5](../../noter5), not a standalone challenge —
it has no player-facing flag or message. It stores the (encrypted) notes and
exposes the vulnerable surface that noter5's proxy sits in front of:

- `/notes` orders results with an un-parameterised `order by timestamp {order}`
  (SQL injection).
- `/activity` returns **all** users' logs globally, leaking the base64 of the
  admin's encrypted flag note. Usernames are base64 in the log too: the proxy
  decrypts every `ENCRYPTED:` value in a response, so a solver's username (the
  flag ciphertext) would otherwise show the decrypted flag to every player.

The proxy seeds the admin and the flag note on start (`noter5/challenge/init.py`,
idempotent). The AES key and the admin password are made when the proxy image is
built, so recreate both containers together: `./ctf.sh reset noter5`.

`solution.py` demonstrates a time-based blind SQL injection over the `order`
parameter. The primary intended path for players goes through the noter5 proxy
(the username decryption oracle) — see [noter5/solution](../../noter5/solution).

## Debrief: what you learn and how to protect against it

There is nothing to solve here on its own; the player-facing task is
[noter5](../../noter5/solution). The backend still has two real weaknesses that
are worth explaining.

**What you learn:**

- SQL injection in an `order by`. The sort direction comes from the `order`
  parameter and is formatted into the query. Nothing is printed back, so
  `solution.py` asks yes/no questions and measures how long the answer takes
  (time-based blind injection).
- Broken access control: `/activity` returns every user's log entries, not only
  your own. That is how the admin's encrypted note leaks.

**The solve in short (the alternative path in `solution.py`):**

1. Register and log in.
2. Send an `order` value where the database only does slow work when a guess
   about the data is right.
3. Time the responses and build up the answer one character at a time.

**How to protect against it:**

- An `order by` direction cannot be a query parameter (`?`), so check it against
  an allow-list: accept only `asc` or `desc` and fall back to a default.
- Filter the activity log on the logged-in user, like `/notes` does.
- The backend should not trust everything that comes through the proxy. Keep it
  off the public network and still validate input and check access there
  (defence in depth).
