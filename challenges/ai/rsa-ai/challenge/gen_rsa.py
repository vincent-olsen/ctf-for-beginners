#!/usr/bin/env python3
"""Build the rsa-ai challenge parameters: two RSA keys, broken in order.

The first version of this challenge was one key with a small private exponent,
and an assistant ran Wiener's attack in under a minute (e almost as large as n
is a well-known tell). Now that is only the first lock:

  1. The OLD key (n1, e1, c1): 2048-bit, large independent primes, but a small
     d, so Wiener's attack (continued fraction of e1/n1) recovers d1. c1 is a
     memo with a "round one flag" in it: a DECOY that CTFd rejects (an assistant
     solving the two-stage draft stopped nowhere near it, because that memo said
     where the flag was; this one doesn't).
  2. The NEW key (n2, e2 = 3, c2): two random 512-bit primes. The memo leaks
     the LOW 362 bits of the private exponent d2 (a damaged backup tape). That is
     a partial key exposure (Boneh, Durfee and Frankel): from e*d = 1 + k*phi
     with k in {1, 2} (since e = 3), the leak gives p + q mod 2^362, so p mod
     2^362 is a root of x^2 - s*x + n2 (mod 2^362), found by lifting bit by bit
     (a few candidates). The top 150 bits of p are then Coppersmith's method
     with known LOW bits: a small root of 2^362*y + p0 modulo an unknown factor
     of n2, by lattice reduction (LLL). The flag is padded with random bytes so
     that m^3 > n2: no cube-root shortcut. c2 decrypts to the flag.
     (Earlier drafts: q as p with its bits mirrored fell in four tool calls, and
     the top of p leaked directly fell in three. This version needs the
     derivation from d's bits to p's bits before Coppersmith even starts.)

Deterministic (seeded), so the shipped rsa.txt is reproducible. Needs nothing
beyond the standard library.
Run:  python3 gen_rsa.py   -> writes ../distfiles/rsa.txt
"""
import math
import random
from pathlib import Path

SEED = 20260927
OLD_BITS = 1024     # per prime of the old key; n1 is 2048-bit
D_BITS = 200        # old key's private exponent: under Wiener's bound n1^(1/4)/3 (~510 bits)
NEW_BITS = 512      # per prime of the new key; n2 is 1024-bit
KNOWN_BITS = 362    # low bits of d2 the memo gives; p's top 150 bits stay unknown
FLAG = b"flag{low_bits_of_d_gave_away_p}"
DECOY = b"flag{small_d_was_only_the_first_door}"


def memo(d_low):
    return (b"Memo. Round one flag: " + DECOY + b". New key: e = 3. Its d is on "
            b"a damaged backup tape, only the low end survived: d mod 2^"
            + str(KNOWN_BITS).encode() + b" = " + hex(d_low).encode())

SMALL_PRIMES = [p for p in range(3, 2000) if all(p % k for k in range(2, int(p ** 0.5) + 1))]


def is_probable_prime(n, rng, rounds=40):
    if n < 2:
        return False
    for p in [2] + SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        a = rng.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def next_prime(n, rng):
    n |= 1
    while not is_probable_prime(n, rng):
        n += 2
    return n


def old_key(rng):
    """Wiener-weak: large independent primes, small d, so e is about as large as n."""
    p = next_prime(rng.getrandbits(OLD_BITS) | (1 << (OLD_BITS - 1)), rng)
    q = next_prime(rng.getrandbits(OLD_BITS) | (1 << (OLD_BITS - 1)), rng)
    n, phi = p * q, (p - 1) * (q - 1)
    bound = math.isqrt(math.isqrt(n)) // 3
    while True:
        d = next_prime(rng.getrandbits(D_BITS) | (1 << (D_BITS - 1)), rng)
        if d < bound and math.gcd(d, phi) == 1:
            return n, pow(d, -1, phi), d


def new_key(rng):
    """RSA with e = 3: two random 512-bit primes, both 2 mod 3 so 3 is invertible."""
    e = 3
    while True:
        top = 3 << (NEW_BITS - 2)  # top two bits set, so n2 is a full 1024 bits
        p = next_prime(rng.getrandbits(NEW_BITS) | top, rng)
        q = next_prime(rng.getrandbits(NEW_BITS) | top, rng)
        phi = (p - 1) * (q - 1)
        if p != q and math.gcd(e, phi) == 1:
            return p * q, e, pow(e, -1, phi), p, q


def main():
    rng = random.Random(SEED)
    n1, e1, d1 = old_key(rng)
    n2, e2, d2, p, q = new_key(rng)
    # The flag, a newline, then random padding: m2^3 is far above n2, so taking a
    # plain cube root of c2 gives nothing.
    padded = FLAG + b"\n" + bytes(rng.randrange(1, 256) for _ in range(80))
    m1, m2 = int.from_bytes(memo(d2 % (1 << KNOWN_BITS)), "big"), int.from_bytes(padded, "big")
    assert m1.bit_length() < n1.bit_length() - 8 and m2 < n2, "message too long for its modulus"
    assert m2 ** 3 > n2 * 2 ** 64, "padding too short: a cube root would leak the flag"
    c1, c2 = pow(m1, e1, n1), pow(m2, e2, n2)

    out = (
        "# Two keys from the cipher office: the old one and the new one.\n"
        f"n1 = {n1}\ne1 = {e1}\nc1 = {c1}\n\n"
        f"n2 = {n2}\ne2 = {e2}\nc2 = {c2}\n"
    )
    (Path(__file__).resolve().parent.parent / "distfiles" / "rsa.txt").write_text(out)

    assert pow(c1, d1, n1) == m1 and pow(c2, d2, n2) == m2, "round-trip failed"
    print(f"old key: n1 {n1.bit_length()} bits, d1 {d1.bit_length()} bits, e1 {e1.bit_length()} bits")
    print(f"new key: n2 {n2.bit_length()} bits, e = 3, memo leaks d mod 2^{KNOWN_BITS}; "
          f"memo {len(memo(d2 % (1 << KNOWN_BITS)))} bytes; wrote rsa.txt")


if __name__ == "__main__":
    main()
