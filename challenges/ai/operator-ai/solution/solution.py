#!/usr/bin/env python3
"""Break operator-ai's reused one-time pad. Reads ../distfiles/flag.enc.

The messages are telegrams (capitals, no spaces, STOP), so the usual space
trick does not apply. Step 1 is statistics: per column, the pad byte that turns
every message into likely telegram characters. It gets about 70%, and not the
flag. Step 2 is what a solver does next: correct a telegram by reading it
(crib-dragging), turn the correction into pad bytes (pad = c ^ m) and decrypt
everything with them.
"""
import math
from pathlib import Path

cts = [bytes.fromhex(line) for line in
       (Path(__file__).resolve().parent.parent / "distfiles" / "flag.enc").read_text().split()]
width = max(len(c) for c in cts)

# Telegram characters, and how common each letter is in English (percent).
ALPHABET = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789{}_")
FREQ = dict(zip(b"ETAOINSHRDLCUMWFGYPBVKJXQZ", [12.7, 9.1, 8.2, 7.5, 7.0, 6.7, 6.3, 6.1, 6.0, 4.3, 4.0, 2.8, 2.8,
                                                 2.4, 2.4, 2.2, 2.0, 2.0, 1.9, 1.5, 1.0, 0.8, 0.15, 0.15, 0.1, 0.07]))


def score(column_bytes):
    if not all(b in ALPHABET for b in column_bytes):
        return float("-inf")  # every telegram character must stay a telegram character
    return sum(math.log(FREQ.get(b, 0.5)) for b in column_bytes)


def show(pad):
    for c in cts:
        print("  ", bytes(x ^ p for x, p in zip(c, pad)).decode("latin-1"))


# Step 1: per column, the pad byte that makes the column look most like English.
pad = bytearray(width)
for col in range(width):
    column = [c[col] for c in cts if len(c) > col]
    pad[col] = max(range(256), key=lambda k: score([b ^ k for b in column]))
print("Step 1, statistics only (close, but the flag line is wrong):")
show(pad)

# Step 2: crib-drag. Step 1's first telegram starts "MORNINATEPORSSTHPNKRTHGATEOPEN",
# which is surely "MORNING REPORT STOP NORTH GATE OPEN...". Each word you are
# sure of gives pad bytes, which clean up the other telegrams in the same
# columns and suggest the next word. After a few rounds the first telegram
# reads in full, and as the longest line it gives the whole pad.
guess = b"MORNINGREPORTSTOPNORTHGATEOPENSATSIXANDCLOSESATNINESHARPSTOP"
pad = bytearray(c ^ m for c, m in zip(cts[0], guess))
print("\nStep 2, after correcting one message:")
show(pad)

for c in cts:
    plain = bytes(x ^ p for x, p in zip(c, pad))
    if b"FLAG{" in plain:
        flag = plain[plain.index(b"FLAG{"):plain.index(b"}") + 1].decode().lower()
        print("\nflag (CTFd flags are case-insensitive):", flag)
