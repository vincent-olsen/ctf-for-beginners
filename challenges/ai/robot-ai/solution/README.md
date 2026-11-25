# robot-ai (AI-modus)

The original `marvin` taught `robots.txt`: the disallowed path `/secret` held the
flag. This variant keeps the robots.txt breadcrumb but puts a **JWT
authentication bypass** behind it. It is **black-box** by default — no source is
attached; the full `app.py` is a paid hint, so reading the code is a deliberate
(paid) step rather than a freebie.

## Chain

1. **robots.txt.** The task points there (as `marvin` did). `GET /robots.txt`
   disallows `/diagnostics`.
2. **/diagnostics.** Loading it sets a `marvin_session` cookie — a JWT
   (`{"alg":"HS256"}`, payload `{"role":"guest"}`). The page and the source both
   note the flag is in `/admin`, which needs `role: admin`.
3. **/admin as guest → 403.** You need an admin token, but you don't have the
   signing secret (it's a long random value in the environment).
4. **The bug (`alg:none`).** In `app.py`, `verify_token()` does:

   ```python
   alg = header.get("alg", "")
   if alg == "none":
       return payload          # <-- accepts an UNSIGNED token
   if alg == "HS256":
       ... verify HMAC ...
   ```

   So a token whose header says `{"alg":"none"}` is accepted with **no signature
   check**. Forge one with `role: admin` and an empty signature; the secret is
   never needed.
5. **/admin with the forged cookie → flag.**

## Run the exploit

[`solve.py`](solve.py) does the whole chain:

```bash
python3 solve.py http://<host>:<port>      # e.g. http://localhost:5006
```

Or by hand, e.g. in CyberChef / jwt.io: take the guest JWT, set the header to
`{"alg":"none","typ":"JWT"}`, set the payload to `{"role":"admin"}`, drop the
signature (keep the trailing dot), and send it as the `marvin_session` cookie to
`/admin`.

This is a classic finding an assistant spots from the source — which is the
point of the AI bracket. Black-box, it still has to *know* the `alg:none` attack
(or buy the source hint): the `/diagnostics` page points you at the token and
`/admin`, but it does **not** spell out the bug.

## Flag

```
flag{alg_n0ne_lets_any_r0bot_in}
```

## Note for organisers

The real fix is to reject `alg:none` (and pin the expected algorithm). The
challenge ships the vulnerable version on purpose; the flag and the signing
secret come from the environment (`Dockerfile`), never from the source — which,
when a player buys the source hint, discloses the code but not the secrets.

## Debrief: what you learn and how to protect against it

**What you learn:** how a JWT (JSON Web Token) is built (header, payload,
signature) and the `alg: none` attack. The token's own header says which
algorithm secures it, and this server accepts `none`, meaning no signature at
all. Then anyone can write their own token with `role: admin`. The `robots.txt`
lesson from `marvin` is the way in.

**The solve in short:**

1. `/robots.txt` disallows `/diagnostics`.
2. `/diagnostics` sets a `marvin_session` cookie: a JWT with `role: guest`.
3. `/admin` answers 403 for a guest, and the signing secret is unknown.
4. Build a new token: header `{"alg":"none","typ":"JWT"}`, payload
   `{"role":"admin"}`, empty signature (keep the final dot).
5. Send it as the cookie to `/admin` and read the flag.

**How to protect against it:**

- Decide the algorithm on the server and never let the token choose:
  `jwt.decode(token, key, algorithms=["HS256"])`. Reject `none` and everything
  not on the list.
- Use a maintained JWT library and don't write the verification yourself. The
  same mistake in another form is algorithm confusion (RS256 switched to HS256).
- Use a long random signing secret and short-lived tokens.
- Check the role on the server for each request, and keep sensitive paths out of
  `robots.txt`.

## How hard it is for an AI

The first cut leaked the whole bug: an HTML comment on `/diagnostics` read *"our
JWT verifier still accepts the legacy header `{"alg":"none"}`… nobody removed the
TODO,"* so a fresh assistant solved it in **6 tool calls** by just following the
comment. That comment was removed, making it genuinely black-box. A fresh
assistant still solved it in **6 tool calls** (~65 s) — but now on its own
knowledge: it recognised the `marvin_session` JWT, tried `alg:none` because that
is *the* textbook JWT bypass, and even hit a real dead end first (an HS256
weak-secret dictionary attack that found nothing). The solve speed floor is low
because `alg:none` is so well known, but the challenge is now a fair black-box
test of whether you know the attack (and the paid source hint is worth buying),
rather than a page that hands you the answer.

## Solving it with an AI (prompts)

Black-box by default: give the assistant the live URL and let it probe. If you
buy the source hint, hand it `app.py` as well — the bug jumps out of the code.

- **Cold open:** "A Flask app runs at <url>. Enumerate it (start with `robots.txt`), find the authentication vulnerability, and get the flag from `/admin`. Give me a working exploit." (If you have the source hint, add: "`app.py` is attached.")
- **If it stalls:** "The JWT verifier accepts `alg: none`. Grab the guest session JWT that `/diagnostics` sets, then forge a token with header `{\"alg\":\"none\",\"typ\":\"JWT\"}`, payload `{\"role\":\"admin\"}`, and an empty signature (keep the trailing dot). Send it as the `marvin_session` cookie to `/admin`. Give me a Python script or the exact curl."

## Difficulty-tuning re-test (2026-11)

A fresh zero-context agent solved it clean in **7 tool calls** (robots.txt -> JWT `alg:none`), at the baseline floor. The solve path is unchanged by the 2h45-event tuning pass; what changed is
hint pricing: 35/60/90 -> 35/120/150 (near-answer/source hints repriced toward their marginal value,
no cost lowered). Full cross-challenge detail in [docs/ai-difficulty-tuning.md](../../../../docs/ai-difficulty-tuning.md).
