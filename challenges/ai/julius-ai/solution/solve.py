#!/usr/bin/env python3
"""Break julius-ai, a running-key cipher. Reads ../distfiles/cipher.txt.

1. Show that the key does not repeat: the index of coincidence is flat (about
   0.04, random text) for every key length, so Kasiski/IoC tools find nothing.
2. Crib the end. "FLAG" before the brace is certain; guess the words before it
   ("...FOR THE ARCHIVE IS"). Subtracting the guess leaves Latin as key:
   "...SPROELIISCUMGERMANI", "(...)s proeliis cum Germani(s)". That is Caesar,
   De Bello Gallico book I chapter 1 (the "Gallia est omnis divisa" chapter).
3. Slide that chapter along the ciphertext: at one offset the whole message
   turns into English. That offset starts at "Horum omnium fortissimi".
"""
from collections import Counter
from pathlib import Path

TEXT = "".join((Path(__file__).resolve().parent.parent / "distfiles" / "cipher.txt").read_text().split())
LETTERS = [c for c in TEXT if c.isalpha()]

# De Bello Gallico 1.1 (Latin Library spelling); only its letters are used.
DBG_1_1 = (
    "Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae, aliam "
    "Aquitani, tertiam qui ipsorum lingua Celtae, nostra Galli appellantur. Hi "
    "omnes lingua, institutis, legibus inter se differunt. Gallos ab Aquitanis "
    "Garumna flumen, a Belgis Matrona et Sequana dividit. Horum omnium "
    "fortissimi sunt Belgae, propterea quod a cultu atque humanitate provinciae "
    "longissime absunt, minimeque ad eos mercatores saepe commeant atque ea quae "
    "ad effeminandos animos pertinent important, proximique sunt Germanis, qui "
    "trans Rhenum incolunt, quibuscum continenter bellum gerunt. Qua de causa "
    "Helvetii quoque reliquos Gallos virtute praecedunt, quod fere cotidianis "
    "proeliis cum Germanis contendunt, cum aut suis finibus eos prohibent aut "
    "ipsi in eorum finibus bellum gerunt."
)
BOOK = "".join(c for c in DBG_1_1.upper() if c.isalpha())


def ioc(seq):
    n = len(seq)
    return sum(v * (v - 1) for v in Counter(seq).values()) / (n * (n - 1))


def key_under(crib, end):
    """The key letters under a plaintext guess ending at letter index `end`."""
    start = end - len(crib)
    return "".join(chr((ord(c) - ord(p)) % 26 + 65) for c, p in zip(LETTERS[start:end], crib))


def decrypt(key):
    out, ki = [], 0
    for ch in TEXT:
        if ch.isalpha():
            out.append(chr((ord(ch) - ord(key[ki])) % 26 + 65))
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


# 1) No period.
print("average IoC per key length:",
      " ".join(f"{k}:{sum(ioc(LETTERS[i::k]) for i in range(k)) / k:.3f}" for k in range(1, 13)))
print("  (English is about 0.066, random text 0.038: no key length stands out)")

# 2) Crib the end: the letters before the "{" are the key's last stretch.
flag_end = sum(c.isalpha() for c in TEXT[:TEXT.index("{")])
print("crib FLAG                  -> key", key_under("FLAG", flag_end))
print("crib FORTHEARCHIVEISFLAG   -> key", key_under("FORTHEARCHIVEISFLAG", flag_end))

# 3) Slide the chapter along the ciphertext; keep the offset that reads most like English.
COMMON = ("THE", "AND", "ING", "ION", "YOU", "ARE", "FOR", "KEY")
best = max(range(len(BOOK) - len(LETTERS) + 1),
           key=lambda off: sum(decrypt(BOOK[off:]).count(w) for w in COMMON))
plain = decrypt(BOOK[best:])
print(f"\nkey = De Bello Gallico 1.1 from letter {best}: {BOOK[best:best + 30]}...")
print(plain)
print("\nflag (CTFd flags are case-insensitive):", plain[plain.index("{") - 4:].lower())
