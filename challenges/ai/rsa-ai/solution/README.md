# rsa-ai (AI-modus): two keys, broken in order

You're handed `rsa.txt` with two RSA keys from the cipher office: an old one
(`n1`, `e1`, `c1`) and a new one (`n2`, `e2`, `c2`). The first version of this
challenge was only the old key, and an assistant ran Wiener's attack on it in
under a minute. Now that key is only the first door.

## Stage 1: the old key (Wiener)

`n1` is 2048 bits with large, independent primes, so don't factor it. The tell
is the public exponent: `e1` is almost as large as `n1`, the signature of a
**small private exponent** `d1` (200 bits, under Wiener's bound `n^(1/4)/3`).
Expand `e1/n1` as a continued fraction; for the right convergent `k/d`,
`phi = (e1*d - 1)/k` makes `x^2 - (n - phi + 1)x + n = 0` factor `n1`.

`c1` decrypts to a memo:

> Memo. Round one flag: flag{small_d_was_only_the_first_door}. New key: e = 3.
> Its d is on a damaged backup tape, only the low end survived: d mod 2^362 = 0x31642d34...

That "round one flag" is a **decoy**: CTFd rejects it.

## Stage 2: the new key (the low bits of d)

`n2` is a 1024-bit key with two random 512-bit primes, and `e = 3`. The flag in
`c2` is padded with random bytes, so `m^3 > n2` and a plain cube root gives
nothing. You know the low 362 bits of `d`. That is a **partial key exposure**
(Boneh, Durfee and Frankel), and it takes three steps.

1. **Get p + q mod 2^362.** `e*d = 1 + k*phi` with `phi = n - s + 1` and
   `s = p + q`. Since `d < phi` and `e = 3`, `k` is 1 or 2. Mod `2^362`:
   `k*s ≡ k*(n + 1) + 1 - e*d0`. For `k = 2` you lose one bit (divide by 2), so
   you get `s mod 2^361`.
2. **Get p mod 2^t.** `p` is a root of `x^2 - s*x + n`. Lift its roots mod
   `2^t` bit by bit (p is odd; extend each candidate by one bit and keep those
   that still satisfy the congruence). That leaves 4 candidates per `k`.
3. **Get the top bits: Coppersmith with known low bits.** `p = 2^t*y + p0` with
   `y < 2^(512-t)` (about 2^150). Make it monic,
   `f(y) = y + p0 * 2^-t mod n`. It has the small root `y0` modulo `p`, an
   unknown factor of `n` of size about `n^(1/2)`, so lattice reduction finds it.
   Then `gcd(f(y0), n) = p`.
   - **In SageMath** (free at [SageMathCell](https://sagecell.sagemath.org/)):

     ```
     F.<y> = PolynomialRing(Zmod(n2))
     f = y + p0 * inverse_mod(2^t, n2)
     f.small_roots(X=2^(512 - t), beta=0.49)
     ```

   - **In plain Python:** LLL on the 4x4 lattice of `N^2`, `N*f`, `f^2`,
     `y*f^2` (scaled by `X`), and the first short vector is a polynomial with
     `y0` as an integer root.

   Here `k = 2` is the right case. For the `k = 1` candidates the lattice gives
   nothing.

Then `d2 = 3^-1 mod (p-1)(q-1)` decrypts `c2`, and the flag is the first line
(the padding follows).

[`solve.py`](solve.py) does it all in plain Python, under a minute:

```bash
python3 solve.py     # reads ../distfiles/rsa.txt
```

## Flag

```
flag{low_bits_of_d_gave_away_p}
```

The decoy `flag{small_d_was_only_the_first_door}` is not accepted.

## How hard it is for an AI

Each version was given to a fresh assistant with only `rsa.txt` and "What is
the ctf flag?": the Wiener-only original fell in one command; a draft with a
bit-mirrored `q` in four tool calls; a draft that leaked the top of `p` directly
in three (LLL written by hand on the first try). This version needs the
derivation from `d`'s bits to `p`'s bits before Coppersmith even starts.

A 2026-11 re-test gave this version its first clean blind solve (the earlier
attempt was cut short by a safety classifier before stage 2). A fresh assistant
took ~22 tool calls: Wiener on the old key, then the partial-key-exposure
derivation and Coppersmith (Howgrave-Graham via fpylll/LLL) on the new one, with
deep dead ends — an mpmath overflow on the huge-coefficient polynomials, and a
mod-`N` coefficient-reduction bug that silently broke the lattice until a
synthetic known-answer test exposed it. It rejected the round-one decoy. So the
challenge is hard but solvable by a capable assistant, not a 3-4 call pushover.

## Regenerating

`challenge/gen_rsa.py` is seeded, so `distfiles/rsa.txt` is reproducible.

## Solving it with an AI (prompts)

Paste `rsa.txt`.

- **Cold open:** "Two RSA keys, n1/e1/c1 and n2/e2/c2. Find the weakness in each and decrypt both ciphertexts."
- **After stage 1:** "The memo's 'round one flag' is a decoy. For the new key e = 3 and I know d mod 2^362. That's a partial key exposure: derive p+q mod 2^362 (k is 1 or 2), lift p mod 2^362 from x^2 - s*x + n, then Coppersmith with known low bits for the rest of p. Give me SageMath code for SageMathCell, or plain Python with its own LLL."

## Difficulty-tuning re-test (2026-11)

A fresh zero-context agent solved it clean in **36 tool calls** (Wiener -> partial-key-exposure -> Coppersmith), rejecting the round-one decoy; hard but solvable by a capable agent. The solve path is unchanged by the 2h45-event tuning pass; what changed is
hint pricing: 30/90 -> 30/150 (near-answer/source hints repriced toward their marginal value,
no cost lowered). Full cross-challenge detail in [docs/ai-difficulty-tuning.md](../../../../docs/ai-difficulty-tuning.md).
