#!/usr/bin/env python3
"""Solve mono-ai without the key: undo the transposition, then a homophonic
substitution solver.

Step 1. The shipped stream was written in rows of W tokens and read off by
columns. Find W: for each width, rebuild the rows and look at the punctuation
tokens. Only the right width puts <{> before every <_> and <}> at the end, with
the flag's pieces close together, like a real flag.

Step 2. Simulated annealing over token -> letter maps, scored on English quadgram
statistics (within the runs between the literal <.> <,> <:> <{> <_> <}> tokens)
plus a small penalty for letter counts far from English. Needs a quadgram count
file, one "QUAD COUNT" per line: the usual english_quadgrams.txt (from
practicalcryptography.com, "TION 13168375" on its first line).

    python3 solve.py english_quadgrams.txt [../distfiles/cipher.txt]

Takes about a minute (step 2). It gets ~96% of the letters; the rest are rare letters
that have a single token each (k, p, x), which come out as a common one. Read
the text and fix them: "masss" is "masks", "stace" is "space".
"""
import math
import random
import re
import sys
from pathlib import Path

ENGLISH = dict(zip("abcdefghijklmnopqrstuvwxyz", (
    8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15, 0.77, 4.0, 2.4,
    6.7, 7.5, 1.9, 0.095, 6.0, 6.3, 9.1, 2.8, 0.98, 2.4, 0.15, 2.0, 0.074)))
LETTERS = range(26)


def load_quadgrams(path):
    counts = {}
    for line in Path(path).read_text().split("\n"):
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 4 and parts[0].isalpha():
            gram = [ord(c) - 97 for c in parts[0].lower()]
            counts[((gram[0] * 26 + gram[1]) * 26 + gram[2]) * 26 + gram[3]] = int(parts[1])
    total = sum(counts.values())
    table = [math.log10(0.01 / total)] * 26 ** 4
    for index, count in counts.items():
        table[index] = math.log10(count / total)
    return table


def solve(tokens, quad, restarts=5, iterations=400_000, seed=1):
    symbols = sorted({t for t in tokens if not t.startswith("<")})
    sym = {t: i for i, t in enumerate(symbols)}
    seq = [sym.get(t, -1) for t in tokens]  # -1: a literal, which breaks the run
    starts = [i for i in range(len(seq) - 3) if min(seq[i:i + 4]) >= 0]
    windows = [set() for _ in symbols]  # the quadgrams each symbol appears in
    for i in starts:
        for s in seq[i:i + 4]:
            windows[s].add(i)
    windows = [sorted(w) for w in windows]
    uses = [seq.count(s) for s in range(len(symbols))]
    expect = [ENGLISH[chr(97 + l)] / 100 * sum(uses) for l in LETTERS]

    def penalty(letter, count):
        return -(count - expect[letter]) ** 2 / (expect[letter] + 1)

    def quads(key, ws):
        return sum(quad[((key[seq[i]] * 26 + key[seq[i + 1]]) * 26 + key[seq[i + 2]]) * 26 + key[seq[i + 3]]] for i in ws)

    rng = random.Random(seed)
    best, best_key = -math.inf, None
    for _ in range(restarts):
        key = [rng.randrange(26) for _ in symbols]
        counts = [0] * 26
        for s, letter in enumerate(key):
            counts[letter] += uses[s]
        score = quads(key, starts) + sum(penalty(l, counts[l]) for l in LETTERS)
        for it in range(iterations):
            temp = 20.0 * (1 - it / iterations) + 1e-9
            s, new = rng.randrange(len(symbols)), rng.randrange(26)
            old = key[s]
            if new == old:
                continue
            delta = -quads(key, windows[s])
            key[s] = new
            delta += quads(key, windows[s])
            delta += (penalty(old, counts[old] - uses[s]) - penalty(old, counts[old])
                      + penalty(new, counts[new] + uses[s]) - penalty(new, counts[new]))
            if delta >= 0 or rng.random() < math.exp(delta / temp):
                score += delta
                counts[old] -= uses[s]
                counts[new] += uses[s]
            else:
                key[s] = old
        if score > best:
            best, best_key = score, key[:]
    return "".join(t[1:-1] if t.startswith("<") else chr(97 + best_key[sym[t]]) for t in tokens)


def untranspose(tokens, width):
    order = [i for col in range(width) for i in range(col, len(tokens), width)]
    out = [None] * len(tokens)
    for src, dst in enumerate(order):
        out[dst] = tokens[src]
    return out


def find_width(tokens):
    """Widths whose rebuilt rows end in a plausible flag: <{> ... <_> ... <}>."""
    good = []
    for width in range(2, 80):
        rows = untranspose(tokens, width)
        lits = [(i, t) for i, t in enumerate(rows) if t in ("<{>", "<_>", "<}>")]
        names = [t for _, t in lits]
        if names and names[0] == "<{>" and names[-1] == "<}>" and "<{>" not in names[1:] \
                and "<}>" not in names[:-1] and lits[-1][0] - lits[0][0] < 80 and lits[-1][0] >= len(rows) - 2:
            good.append(width)
    return good


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    here = Path(__file__).resolve().parent
    cipher = Path(sys.argv[2]) if len(sys.argv) > 2 else here.parent / "distfiles" / "cipher.txt"
    tokens = cipher.read_text().split()
    widths = find_width(tokens)
    print("widths that rebuild a flag-shaped ending:", widths)
    text = solve(untranspose(tokens, widths[0]), load_quadgrams(sys.argv[1]))
    print(text)
    found = re.search(r"flag\{[^}]*\}", text)
    print("flag (fix the odd letter by reading):", found.group(0) if found else "(not found)")


if __name__ == "__main__":
    main()
