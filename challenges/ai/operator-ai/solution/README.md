# operator-ai (AI-modus)

The original `operator` was *keyless*: a chain of reversible integer operations
you inverted step by step. Its flag suggested the sequel, `flag{l3ts_u5e_4_key_n3xt_t1me}`.
The first AI-mode version used a short repeating XOR key, and an assistant broke
it with one script. A long English note under an 8-byte key is the textbook case.

This version uses a **one-time pad**: random bytes as long as the message, which
on its own is unbreakable. But the operator reuses the same pad for all seven
messages of the day, which makes it a **many-time pad**.

Players get:

- `distfiles/encrypt.py`: the scheme, with the messages redacted. One
  `os.urandom` pad, every message XORed with it.
- `distfiles/flag.enc`: seven ciphertexts, one hex line each.

The messages are **telegrams**: capitals, no spaces, `STOP` for a full stop. That
takes away the usual many-time-pad shortcut (a space XOR a letter is that letter
with its case flipped). The flag is leetspeak, so a garbled flag can't be fixed
by guessing words.

## Intended solve

1. **Spot the reuse.** XOR two ciphertexts and the pad cancels:
   `c1 ^ c2 = m1 ^ m2`. Nearly every value is below 0x20, which is what two
   capital letters give, so the messages are in capitals.
2. **Statistics.** For each byte position, keep the pad bytes that turn every
   message into capitals, digits or `{}_`, and pick the one that gives the most
   common letters. That gets about 70% of the characters:

   ```
   MORNINATEPORSSTHPNKRTHGATEOPENITTE_YAIDYLLSESATNIRESHTDAHHLE
   SUPPLYRTUCKLFTEEECEUSEOFSNOWSTUEENFDCSINAETERLUNCTTODTOBOSS
   ...
   ARCHIVCVASSWHRDNSFHAG{0NE_T1MEEE4RIL4IYET2ME5}STOL
   ```
3. **Crib-drag.** Read the telegrams that are nearly right ("MORNINATEPORSSTHPNKRTH..."
   is surely "MORNINGREPORTSTOPNORTH..."). Every byte you are sure of gives a
   pad byte (`pad = c ^ m`). That fixes the same column in the other six
   telegrams and suggests the next word. Repeat until one telegram that covers the
   flag's columns reads in full. Every telegram is at least as long as the flag
   line, so any of them will do.
4. Decrypt the flag line with the corrected pad:
   `ARCHIVEPASSWORDISFLAG{0NE_T1ME_P4D_M4NY_T1ME5}STOP`.

[`solution.py`](solution.py) does steps 2 and 4 and shows the state before and
after one corrected telegram:

```bash
python3 solution.py     # reads ../distfiles/flag.enc
```

The ciphertext is rebuilt from [`../challenge/encrypt.py`](../challenge/encrypt.py)
(seeded, so reproducible).

## Flag

```
flag{0ne_t1me_p4d_m4ny_t1me5}
```

(It is upper case in the telegram; CTFd flags are case-insensitive.)

## How hard it is for an AI

A draft with ordinary sentences (spaces, lower case) fell to a fresh assistant in
six tool calls: the space trick got most of it, and three cribs finished it.
Telegram style is there to take the space trick away. With it, the same test
took 14 tool calls. Two dead ends: lower-case assumptions that turned `FLAG{`
into control characters, and two crib guesses that contradicted each other.

A 2026-11 re-test reproduced this: a fresh assistant solved it in ~18 tool
calls, pinning the pad with `STOP` cribs and a beam search over the columns,
with the same weak-heuristic dead ends (per-column frequency and space-XOR give
too little with only seven short messages).

## Solving it with an AI (prompts)

Give it `encrypt.py` and `flag.enc`.

- **Cold open:** "Attached is `encrypt.py` and `flag.enc` (hex, one message per line). Recover the plaintexts; one of them contains a `flag{...}`."
- **If it stalls:** "The same pad is reused for every line, so it is a many-time pad. The messages are telegrams: capitals, no spaces, STOP. For each column keep only pad bytes that make every line A-Z, 0-9 or `{}_`, and score by English letter frequency. Then show me the result so we can crib-drag."
- **Crib-dragging together:** "Line 1 reads like `MORNINGREPORTSTOPNORTHGATEOPEN...`. Fix it to that, derive the pad bytes, and print all lines again."

## Difficulty-tuning re-test (2026-11)

A fresh zero-context agent solved it clean in **24 tool calls** (many-time-pad crib-dragging), near the chat-sized budget. The solve path is unchanged by the 2h45-event tuning pass; what changed is
hint pricing: 30/80 -> 30/130 (near-answer/source hints repriced toward their marginal value,
no cost lowered). Full cross-challenge detail in [docs/ai-difficulty-tuning.md](../../../../docs/ai-difficulty-tuning.md).
