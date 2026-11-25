#!/usr/bin/env python3
"""Build the julius-ai ciphertext.

The original `julius` challenge is a Caesar cipher (one fixed shift). The first
AI-mode version stepped up to Vigenere with an 8-letter key, which an assistant
breaks in two commands: a short key repeats, and Kasiski / index of coincidence
count the repeats. So this version uses a key that never repeats.

It is a *running-key* cipher: Vigenere addition (A=0 ... Z=25), but the key is a
text as long as the message, a passage of Caesar's own Commentarii de Bello
Gallico, book I chapter 1, letters only, starting at "Horum omnium fortissimi
sunt Belgae" (not at the famous "Gallia est omnis divisa"). There is no period,
so period analysis finds nothing.

The ciphertext is written the classical way, in groups of five capitals with
the spaces, case and punctuation of the plaintext removed, so word lengths and
capitals give no cribs. Only the flag at the end keeps its braces and
underscores (they pass through unchanged and use no key), so the flag's shape
stays readable.

The solve is a crib: "flag" before the brace is certain, the words before it
can be guessed ("...for the archive is"); subtracting them leaves a scrap of
Latin key. Recognise it as Caesar, take book I chapter 1 and slide it along the
ciphertext until English appears. (Players can look the text up, e.g. on the
Latin Library; an assistant usually knows it by heart.)

Run from this directory:  python3 makecipher.py
It (re)writes ../distfiles/cipher.txt and prints a round-trip check.
"""
from pathlib import Path

# Caesar, De Bello Gallico 1.1, in the common Latin Library spelling (i and v,
# no j or u-for-v). Only its letters are used, lowercased, from KEY_START on.
KEY_TEXT = (
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

KEY_START = "Horum omnium fortissimi"

PLAINTEXT = (
    "To the cipher office of Rome. You broke my single shift in an afternoon, "
    "and you broke the marching word before supper, because a short key must "
    "repeat and whatever repeats can be counted. So my new key does not repeat. "
    "It is as long as this letter, and it is not random either: it is a page "
    "from a book that every schoolboy will one day be made to copy, written by "
    "the only author I trust. Count all you like. My seal for the archive is "
    "flag{all_gaul_is_the_key}"
)


def key_letters(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalpha())


def encrypt(plaintext: str, key: str) -> str:
    out, ki = [], 0
    for ch in plaintext.upper():
        if ch.isalpha():
            out.append(chr((ord(ch) - 65 + ord(key[ki]) - 97) % 26 + 65))
            ki += 1
        elif ch in "{}_":
            out.append(ch)
    return "".join(out)


def decrypt(cipher: str, key: str) -> str:
    out, ki = [], 0
    for ch in cipher:
        if ch.isalpha():
            out.append(chr((ord(ch) - 65 - (ord(key[ki]) - 97)) % 26 + 65))
            ki += 1
        elif ch in "{}_":
            out.append(ch)
    return "".join(out)


def groups_of_five(cipher: str) -> str:
    """The body in five-letter groups, ten to a line; the flag kept whole at the end."""
    body, flag = cipher[:cipher.index("{") - 4], cipher[cipher.index("{") - 4:]
    groups = [body[i:i + 5] for i in range(0, len(body), 5)]
    lines = [" ".join(groups[i:i + 10]) for i in range(0, len(groups), 10)]
    return "\n".join(lines) + "\n" + flag + "\n"


def main() -> None:
    here = Path(__file__).resolve().parent
    full = key_letters(KEY_TEXT)
    start = full.index(key_letters(KEY_START))
    key = full[start:]
    used = sum(c.isalpha() for c in PLAINTEXT)
    assert used <= len(key), "plaintext is longer than the key text"
    cipher = encrypt(PLAINTEXT, key)
    (here.parent / "distfiles" / "cipher.txt").write_text(groups_of_five(cipher))
    # Round-trip check, from the file as shipped, so it always matches the solution.
    shipped = "".join((here.parent / "distfiles" / "cipher.txt").read_text().split())
    expected = "".join(c for c in PLAINTEXT.upper() if c.isalpha() or c in "{}_")
    assert decrypt(shipped, key) == expected, "round-trip failed"
    print(f"key: {used} letters of De Bello Gallico 1.1, from letter {start} (\"{KEY_START}...\")")
    print(groups_of_five(cipher))
    print("decrypts to:", decrypt(shipped, key)[-60:])


if __name__ == "__main__":
    main()
