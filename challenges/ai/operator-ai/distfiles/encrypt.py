#!/usr/bin/env python3
# The encryptor that produced flag.enc.
# You broke my repeating key in under a second. Fine: no more short keys.
# Every message now gets a one-time pad, random bytes as long as the message.
# A one-time pad is mathematically unbreakable. Everybody says so.
#
# flag.enc holds one line of hex per message: today's radio traffic.

import os


def encrypt(message: bytes, pad: bytes) -> bytes:
    return bytes(m ^ p for m, p in zip(message, pad))


if __name__ == "__main__":
    messages = [b"REDACTED", ...]  # today's telegrams (one of them holds the flag)
    pad = os.urandom(max(len(m) for m in messages))  # today's pad
    with open("flag.enc", "w") as f:
        for m in messages:
            f.write(encrypt(m, pad).hex() + "\n")
