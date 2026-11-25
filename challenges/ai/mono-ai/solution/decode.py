#!/usr/bin/env python3
"""Decode mono-ai once the homophone map is known.

This undoes the transposition (rows of `width`, read by columns) and applies the
recovered mapping (token -> letter) to confirm the plaintext. It reads both from
../challenge/key.txt (the "answer key" a solver rebuilds) and the ciphertext
from ../distfiles/cipher.txt. solve.py recovers (most of) that blind; see
README.md.
"""
import re
from pathlib import Path

here = Path(__file__).resolve().parent
key_line = (here.parent / "challenge" / "key.txt").read_text().strip()

# token -> plaintext letter
rev = {}
width = None
for part in key_line.split(";"):
    letter, toks = part.strip().split(":")
    if letter == "width":
        width = int(toks)
        continue
    for t in toks.split("|"):
        rev[t] = letter

shipped = (here.parent / "distfiles" / "cipher.txt").read_text().split()
# Undo the transposition: the shipped order is the rows read off by columns.
order = [i for col in range(width) for i in range(col, len(shipped), width)]
tokens = [None] * len(shipped)
for src, dst in enumerate(order):
    tokens[dst] = shipped[src]
# One flat stream of space-separated tokens (no word boundaries). Spaces between
# words are not encoded, so the recovered plaintext comes out unspaced; the flag
# is delimited by its own <{> ... <}> literals.
out = []
for tok in tokens:
    if tok.startswith("<") and tok.endswith(">"):
        out.append(tok[1:-1])   # literal (the flag's { } _ and digits)
    else:
        out.append(rev[tok])
text = "".join(out)
print(text)
mobj = re.search(r"flag\{[^}]*\}", text)
print("flag:", mobj.group(0) if mobj else "(not found)")
