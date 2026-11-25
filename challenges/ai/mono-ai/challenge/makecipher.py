#!/usr/bin/env python3
"""Build the mono-ai ciphertext.

The original `mono` challenge is a monoalphabetic substitution: one cipher
letter per plaintext letter, so `tr` (once you guess the key) or a frequency
count cracks it. This AI-mode variant uses a *homophonic* substitution: common
letters map to SEVERAL cipher tokens (two-digit numbers), and the encoder
spreads a letter's occurrences across its tokens. That flattens the frequency
histogram, so a naive count is useless -- solvers need an automated homophonic
solver or an LLM that reasons over word patterns.

Word boundaries are REMOVED: the output is one flat stream of space-separated
tokens, so there are no word-length or word-pattern cribs. A solver must run an
automated homophonic/cryptogram solver (e.g. simulated annealing scored on
English n-gram statistics) instead of leaning on word structure.

That only works when the text is long enough for the number of tokens: with
100 tokens over ~380 letters, wrong decryptions score better on quadgrams than
the real one, so no solver can find it. ~70 tokens over ~640 letters puts the
real text on top; ../solution/solve.py (no key) recovers it but for a few
rare single-token letters, which you fix by reading (masss -> masks).

An assistant still ran that solver in nine commands. So the token stream is now
also TRANSPOSED before it is shipped, the way the Zodiac's Z340 was: written in
rows of WIDTH tokens and read off column by column, top to bottom, left to right
(the last row is short). Quadgram scoring on the shipped order finds nothing,
because neighbouring tokens are no longer neighbouring letters. The punctuation
tokens are transposed with everything else, and that is the tell: <}> turns up
before <{>, and the flag's <_> are scattered all over the stream. Undo the
transposition (try each width until the flag's <{> _ _ _ <}> line up again near
the end), then solve the homophonic substitution as before.

Deterministic: a fixed seed makes the mapping and the output reproducible.
Run:  python3 makecipher.py   -> writes ../distfiles/cipher.txt (+ key.txt for us)
"""
import random
from collections import defaultdict
from pathlib import Path

SEED = 20260927
WIDTH = 17  # transposition: rows of 17 tokens, read off by columns (Z340 had 17 columns)

# English letter frequency weights (relative). More frequent -> more tokens,
# so every token ends up used at roughly the same rate: a flat histogram. 70
# tokens in all; more than that and the text below is too short to solve.
FREQ = {
    "a": 5, "b": 1, "c": 2, "d": 2, "e": 8, "f": 1, "g": 1, "h": 4,
    "i": 5, "j": 1, "k": 1, "l": 3, "m": 2, "n": 5, "o": 5, "p": 1,
    "q": 1, "r": 4, "s": 4, "t": 6, "u": 2, "v": 1, "w": 1, "x": 1,
    "y": 1, "z": 1,
}

PLAINTEXT = (
    "a monoalphabetic cipher hands every letter a single mask so counting how "
    "often each mask appears betrays the whole message. here the common letters "
    "wear many masks at once and the writer rotates through them so no single "
    "symbol stands taller than the rest. frequency counting gives you noise. the "
    "spaces between the words are gone as well so you cannot count the letters "
    "in a word or pick out the short ones. and the masks are not even in the "
    "right order: they were written out in rows and read back down the columns, "
    "so the letters that stand next to each other in the language are now far "
    "apart in the stream. put the rows back first. then the language returns: "
    "which letters like to stand together and which never meet. guess a key, "
    "score it on that, keep the better one and keep going until the text starts "
    "to look like english. a solver will do the rest, and the flag is "
    "flag{seventeen_columns_and_many_masks}"
)


def transpose(tokens, width):
    """Write in rows of `width`, read off column by column."""
    return [tokens[i] for col in range(width) for i in range(col, len(tokens), width)]


def untranspose(tokens, width):
    """The inverse: column c holds the tokens of rows 0..k at position c."""
    out = [None] * len(tokens)
    order = [i for col in range(width) for i in range(col, len(tokens), width)]
    for src, dst in enumerate(order):
        out[dst] = tokens[src]
    return out


def main() -> None:
    rng = random.Random(SEED)
    # Assign each letter a pool of distinct three-digit tokens sized by frequency
    # (900 tokens available, far more than the 70 the weights ask for).
    tokens = [f"{n:03d}" for n in range(100, 1000)]
    rng.shuffle(tokens)
    pool = {}
    i = 0
    for letter, weight in FREQ.items():
        pool[letter] = tokens[i : i + weight]
        i += weight

    # Round-robin through each letter's tokens so usage stays even.
    cursor = defaultdict(int)
    out_words = []
    for word in PLAINTEXT.split(" "):
        enc = []
        for ch in word:
            low = ch.lower()
            if low in pool:
                toks = pool[low]
                enc.append(toks[cursor[low] % len(toks)])
                cursor[low] += 1
            else:
                # keep non-letters (the flag's { } _ and digits) as literals in <>
                enc.append(f"<{ch}>")
        out_words.append(" ".join(enc))
    in_order = " ".join(out_words).split()
    cipher = " ".join(transpose(in_order, WIDTH))

    here = Path(__file__).resolve().parent
    (here.parent / "distfiles" / "cipher.txt").write_text(cipher + "\n")

    # A reverse map for the writeup (unique because tokens are distinct).
    rev = {t: l for l, toks in pool.items() for t in toks}
    keyline = f"width:{WIDTH}; " + "; ".join(f"{l}:{'|'.join(toks)}" for l, toks in pool.items())
    (here / "key.txt").write_text(keyline + "\n")

    # Round-trip check. Spaces between words are no longer encoded, so compare
    # against the space-stripped plaintext.
    decoded = []
    for tok in untranspose(cipher.split(), WIDTH):
        if tok.startswith("<") and tok.endswith(">"):
            decoded.append(tok[1:-1])
        else:
            decoded.append(rev[tok])
    assert "".join(decoded) == PLAINTEXT.replace(" ", ""), "round-trip failed"
    print("distinct tokens used:", len({t for t in cipher.split() if not t.startswith('<')}))
    print("cipher head:", cipher[:120], "...")
    assert untranspose(transpose(in_order, WIDTH), WIDTH) == in_order
    print(f"transposed: rows of {WIDTH}, read by columns")
    print("ok, decodes back to the flag:", PLAINTEXT.split()[-1])


if __name__ == "__main__":
    main()
