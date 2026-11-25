# api3 — the script goes brrr

**Category:** web · **Flag:** `flag{scr1pt_g0es_brrrrr}`

The root page points at `/key`, and `/key` points at `/flag`:

```bash
curl http://$HOST:$PORT/key
```

```json
{"api_key":"<48 hex chars>","type":"Bearer","added_at":..., "next":"/flag"}
```

`/flag` wants the key as a bearer token:

```bash
curl http://$HOST:$PORT/flag -H "Authorization: Bearer <api_key>"
```

But there are two catches:

- The key **expires 3 seconds** after `/key` issues it.
- `/flag` only hands over the flag on the **third** call with that key (the first
  two say "just need to verify a couple more times").

So you must call `/key` once and `/flag` three times within 3 seconds — too fast to
do by hand in a browser, but trivial in a script. Run the included solver:

```bash
./solution http://$HOST:$PORT
```

The third response:

```json
{"yay":"🎉🎉🎉🎉🎉🎉","time_left":"...ms","here_you_go":"flag{scr1pt_g0es_brrrrr}"}
```

**Lesson:** when an API enforces a short-lived token and a call count, automate it —
a loop (or a few piped `curl`s) beats clicking.

## Debrief: what you learn and how to protect against it

**What you learn:** to automate. The key lives for 3 seconds and the flag comes
on the third call, which is too fast by hand and trivial for a script. A hacker
(and a developer) writes a few lines of code instead of clicking.

**The solve in short:**

1. `GET /key` returns an API key and points to `/flag`.
2. `GET /flag` with `Authorization: Bearer <key>` must be called three times
   before the key expires.
3. Do steps 1 and 2 in a script or a shell loop (`./solution <url>`); the third
   answer holds the flag.

**How to protect against it:** here the automation is the lesson, not a bug, but
it says something about defence too.

- A time limit only stops people. If you want to stop scripts you need rate
  limiting per client, quotas, and for login-type endpoints lockout or backoff.
- Short-lived tokens are still a good idea, for another reason: a stolen token
  is only useful for a short while.
- Anyone can get a key from `/key` without logging in. A key that is handed out
  to everyone identifies nobody.
