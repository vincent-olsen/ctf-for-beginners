# noter-ai (AI-modus)

`noter` was a "read the source" web challenge. This one keeps that spirit but the
bug is a **blind boolean SQL injection**. The flag lives in a `secrets` table
that no page ever renders — and the search box never prints the rows it matches,
only *whether* anything matched. So a straight `UNION SELECT ... FROM secrets`
no longer leaks the value: you have to pull it out one character at a time.

## The bug

`distfiles/app.py` builds the search query by string concatenation:

```python
sql = "SELECT title, body FROM notes WHERE title LIKE '%" + q + "%'"
```

and renders only a boolean:

```python
matched = con.execute(sql).fetchone() is not None
# -> "Some notes matched your search."  /  "No notes matched."
```

Two columns are selected (`title`, `body`); the flag sits in
`secrets(name, value)`. SQL errors are swallowed (read as "no match"), so a
malformed payload looks false — craft valid SQL.

## Intended solve

1. **Confirm the oracle.** The page says "Some notes matched your search." iff a
   row comes back. `zzz%' OR '1'='1' -- ` matches (comments out the trailing
   `%'`); a term that matches nothing does not. That true/false difference is the
   boolean oracle — the only signal you get.
2. **Make the match depend on the secret.** UNION a row that only appears when a
   guess is right (two columns, to match the SELECT):

   ```
   zzz%' UNION SELECT 1,2 WHERE substr((SELECT value FROM secrets),1,1)='f' -- 
   ```

   "matched" iff the 1st character of the flag is `f`.
3. **Extract character by character.** Binary-search each position on the
   codepoint — `unicode(substr((SELECT value FROM secrets),i,1)) > N` — after
   finding the length with `length((SELECT value FROM secrets))=n`. A few hundred
   requests, trivially scripted.

[`solve.py`](solve.py) automates the whole extraction:

```bash
python3 solve.py http://<host>:<port>     # e.g. http://localhost:5007
# flag: flag{union_select_your_way_in}
```

Recognising the boolean oracle and scripting a per-character extraction is the
AI-tier step — a notable jump from reading a UNION straight off the source.

## Flag

```
flag{union_select_your_way_in}
```

## Note for organisers

The fix is parameterised queries. The challenge ships the vulnerable version on
purpose; the flag comes from the environment (`Dockerfile`) and is stored only in
the `secrets` table, never in the source handed to players.

## Debrief: what you learn and how to protect against it

**What you learn:** blind SQL injection. The page never shows data from the
database, only whether the search matched. That one bit is enough: ask a
yes/no question about the secret in each request ("is character 1 greater than
`m`?") and a script reads it out character by character. Hiding the output does
not fix an injection.

**The solve in short:**

1. Find the injection in the search box: `zzz%' OR '1'='1' -- ` matches, a
   nonsense term does not. That difference is the oracle.
2. Make the match depend on the secret: `UNION SELECT 1,2 WHERE
   substr((SELECT value FROM secrets),1,1)='f'`.
3. Find the length, then binary-search each character on its code point.
4. Script it (`solve.py`): a few hundred requests give the flag.

**How to protect against it:**

- Parameterised queries (or an ORM) for every query. A `LIKE` search is written
  `WHERE title LIKE ?` with the `%` added to the parameter.
- Don't count on hidden output or swallowed errors. They slow the attacker from
  one request to a few hundred, nothing more.
- Least privilege in the database: the account behind the search should not be
  able to read the `secrets` table at all.
- Rate limiting and monitoring catch the pattern: hundreds of near-identical
  searches with SQL keywords from one client.

## How hard it is for an AI

The first cut rendered the matched rows, so a single `UNION SELECT name, value
FROM secrets` dumped the flag: a fresh assistant with `app.py` and "What is the
ctf flag?" solved it in **2 tool calls** (read the source, one request). After
the search was made **blind** (match/no-match only), a fresh assistant solved it
in **5 tool calls** (~80 s): it confirmed the straight UNION no longer leaked,
recognised the boolean oracle, wrote a binary-search extractor, and pulled the
flag out character by character — "a notable step up from a visible-UNION
challenge." The injection point is still obvious from the source (that is the
white-box part); the work is now in the blind extraction.

## Solving it with an AI (prompts)

Give it `app.py` (and the live URL).

- **Cold open:** "Attached is `app.py`; a live copy runs at <url>. The `/search` endpoint builds SQL from user input by string concatenation, but the page only tells you whether a note matched. Get the flag. Give me a script."
- **If it stalls:** "It's a BLIND boolean SQL injection in `/search` — the query is `SELECT title, body FROM notes WHERE title LIKE '%<q>%'` (two columns) and the page prints only 'Some notes matched' vs 'No notes matched'. Make a UNION row appear only when a condition on the secret is true, e.g. `zzz%' UNION SELECT 1,2 WHERE substr((SELECT value FROM secrets),1,1)='f' -- `, and binary-search each character of `secrets.value`. Give me the extraction script."

## Difficulty-tuning re-test (2026-11)

A fresh zero-context agent solved it clean in **6 tool calls** (white-box blind boolean SQLi), consistent with the baseline floor. The solve path is unchanged by the 2h45-event tuning pass; what changed is
hint pricing: 30/80 -> 30/130 (near-answer/source hints repriced toward their marginal value,
no cost lowered). Full cross-challenge detail in [docs/ai-difficulty-tuning.md](../../../../docs/ai-difficulty-tuning.md).
