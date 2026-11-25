#!/usr/bin/env python3
"""Solve rsa-ai: Wiener's attack on the old key, then a partial key exposure on
the new one. Reads ../distfiles/rsa.txt (or a path given). Standard library
only, under a minute (each wrong candidate costs one lattice reduction).

Stage 1. e1 is about as large as n1, the tell for a small d. Expand e1/n1 as a
continued fraction; for the right convergent k/d, phi = (e1*d - 1)/k factors n1.
c1 decrypts to a memo with a decoy "round one flag" and d2 mod 2^362.

Stage 2 (Boneh, Durfee and Frankel). e2 = 3, so e*d = 1 + k*phi with k in {1, 2},
and phi = n - s + 1 with s = p + q. Mod 2^362 that gives s from the leaked low
bits of d (for k = 2 one bit less). p is a root of x^2 - s*x + n, so lift its
roots mod 2^t bit by bit: a handful of candidates p0 = p mod 2^t. For each, the
missing top bits are a small root y of 2^t*y + p0 modulo p, an unknown factor
of n: Coppersmith's method (Howgrave-Graham lattice of N^2, N*f, f^2, x*f^2 for
the monic f(y) = y + p0 * 2^-t mod n, LLL-reduced). In SageMath that step is

    F.<y> = PolynomialRing(Zmod(n2)); f = y + p0 * inverse_mod(2^t, n2)
    f.small_roots(X=2^(512 - t), beta=0.49)
"""
import math
import re
import sys
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "distfiles" / "rsa.txt"
V = {k: int(v) for k, v in re.findall(r"^(\w+)\s*=\s*(\d+)", path.read_text(), re.M)}
n1, e1, c1, n2, e2, c2 = (V[k] for k in ("n1", "e1", "c1", "n2", "e2", "c2"))


def to_bytes(m):
    return m.to_bytes((m.bit_length() + 7) // 8, "big")


# --- stage 1: Wiener -----------------------------------------------------------
def convergents(a, b):
    h0, h1, k0, k1 = 0, 1, 1, 0
    while b:
        q = a // b
        a, b = b, a - q * b
        h0, h1 = h1, q * h1 + h0
        k0, k1 = k1, q * k1 + k0
        yield h1, k1  # k, d


def wiener(e, n):
    for k, d in convergents(e, n):
        if k == 0 or (e * d - 1) % k:
            continue
        phi = (e * d - 1) // k
        s = n - phi + 1  # p + q
        disc = s * s - 4 * n
        if disc >= 0 and math.isqrt(disc) ** 2 == disc:
            return d
    raise SystemExit("Wiener found nothing")


d1 = wiener(e1, n1)
print(f"stage 1: d1 has {d1.bit_length()} bits")
print("  c1 =", to_bytes(pow(c1, d1, n1)).decode())


# --- stage 2: Coppersmith, known high bits of p --------------------------------
from fractions import Fraction


def lll(rows, delta=Fraction(99, 100)):
    """Textbook LLL with exact arithmetic. Slow, but the lattice is 4x4."""
    b = [list(r) for r in rows]
    n = len(b)

    def dot(u, v):
        return sum(x * y for x, y in zip(u, v))

    def gram_schmidt():
        bs, mu = [], [[Fraction(0)] * n for _ in range(n)]
        for i in range(n):
            v = [Fraction(x) for x in b[i]]
            for j in range(i):
                mu[i][j] = Fraction(dot(b[i], bs[j])) / dot(bs[j], bs[j])
                v = [x - mu[i][j] * y for x, y in zip(v, bs[j])]
            bs.append(v)
        return bs, mu

    bs, mu = gram_schmidt()
    k = 1
    while k < n:
        for j in range(k - 1, -1, -1):
            q = round(mu[k][j])
            if q:
                b[k] = [x - q * y for x, y in zip(b[k], b[j])]
                bs, mu = gram_schmidt()
        if dot(bs[k], bs[k]) >= (delta - mu[k][k - 1] ** 2) * dot(bs[k - 1], bs[k - 1]):
            k += 1
        else:
            b[k], b[k - 1] = b[k - 1], b[k]
            bs, mu = gram_schmidt()
            k = max(k - 1, 1)
    return b


def polymul(u, v):
    out = [0] * (len(u) + len(v) - 1)
    for i, x in enumerate(u):
        for j, y in enumerate(v):
            out[i + j] += x * y
    return out


def integer_roots(h, lo, hi):
    """Integer roots of the polynomial h (coefficients, lowest first) in [lo, hi).
    Split the range where h' changes sign (recursively, via the derivative's own
    roots), then bisect each monotone piece. Exact integers throughout."""
    while len(h) > 1 and h[-1] == 0:
        h = h[:-1]
    value = lambda x: sum(c * x ** k for k, c in enumerate(h))
    if len(h) <= 1:
        return []
    cuts = [lo, hi - 1]
    if len(h) > 2:
        dh = [k * c for k, c in enumerate(h)][1:]
        cuts += [r for x in integer_roots(dh, lo, hi) for r in (x, x + 1) if lo <= r < hi]
    cuts = sorted(set(cuts))
    roots = set()
    for left, right in zip(cuts, cuts[1:]):
        vl, vr = value(left), value(right)
        for x, v in ((left, vl), (right, vr)):
            if v == 0:
                roots.add(x)
        if (vl < 0) != (vr < 0):
            while right - left > 1:  # bisect the sign change
                mid = (left + right) // 2
                if (value(mid) < 0) == (vl < 0):
                    left = mid
                else:
                    right = mid
            for x in (left, right):
                if value(x) == 0:
                    roots.add(x)
    return sorted(roots)


def coppersmith(n, a, X, m=2, t=2):
    """Small roots x0 < X of f(x) = a + x modulo an unknown factor of n of size
    about n^(1/2). Returns that factor, gcd(a + x0, n), or None."""
    f = [a, 1]
    powers = [[1]]
    for _ in range(m):
        powers.append(polymul(powers[-1], f))
    polys = [[c * n ** (m - i) for c in powers[i]] for i in range(m)]
    polys += [[0] * j + powers[m] for j in range(t)]
    dim = m + t
    rows = [[(poly[k] * X ** k if k < len(poly) else 0) for k in range(dim)] for poly in polys]
    for row in lll(rows):
        if any(row[k] % X ** k for k in range(dim)):
            continue
        h = [row[k] // X ** k for k in range(dim)]  # h(x0) = 0 over the integers
        for x0 in integer_roots(h, 0, X):
            g = math.gcd(a + x0, n)
            if 1 < g < n:
                return g
    return None


def lift_roots(s, n, bits):
    """All x mod 2^bits with x^2 - s*x + n = 0 (mod 2^bits), lifted bit by bit."""
    roots = [1]  # p is odd
    for i in range(1, bits):
        mod = 1 << (i + 1)
        roots = [r for x in roots for r in (x, x + (1 << i)) if (r * r - s * r + n) % mod == 0]
    return roots


memo = to_bytes(pow(c1, d1, n1)).decode()
match = re.search(r"d mod 2\^(\d+) = (0x[0-9a-f]+)", memo)
t, d_low = int(match.group(1)), int(match.group(2), 16)
p = None
for k in (1, 2):  # e*d = 1 + k*phi, and k < e = 3
    rhs = k * (n2 + 1) + 1 - e2 * d_low  # = k*s (mod 2^t)
    if k == 1:
        s_candidates, bits = [rhs % (1 << t)], t
    else:
        if rhs % 2:
            continue
        s_candidates, bits = [(rhs // 2) % (1 << (t - 1))], t - 1
    for s in s_candidates:
        p0s = lift_roots(s, n2, bits)
        print(f"  k = {k}: {len(p0s)} candidates for p mod 2^{bits}")
        for p0 in p0s:
            a = p0 * pow(1 << bits, -1, n2) % n2
            p = coppersmith(n2, a, 1 << (512 - bits))
            if p:
                break
        if p:
            break
    if p:
        break
q = n2 // p
d2 = pow(e2, -1, (p - 1) * (q - 1))
print(f"stage 2: p = {str(p)[:20]}..., from {t} low bits of d")
plain = to_bytes(pow(c2, d2, n2))
print("  flag:", plain.split(b"\n")[0].decode(), "(followed by random padding)")
