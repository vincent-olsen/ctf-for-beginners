# mono-ai (AI-modus)

The original `mono` is a monoalphabetic substitution: exactly one cipher symbol
per plaintext letter. Count how often each symbol appears, line it up with
English letter frequency (`e`, `t`, `a`, ...), and `tr` finishes it.

This variant has two layers:

1. A **homophonic substitution.** Each plaintext letter maps to *several* cipher
   tokens (three-digit numbers), and the writer rotates through a letter's tokens
   as it is used. That gives 67 distinct tokens, each appearing at roughly the
   same rate, so the frequency histogram is flat. Word gaps are gone. Punctuation
   stays as literal tokens: `<.>`, `<,>`, `<:>`, `<{>`, `<_>`, `<}>`.
2. A **transposition**, the way the Zodiac's Z340 cipher was built: the token
   stream was written in rows of **17** and read off **column by column** (top to
   bottom, left to right; the last row is short).

The first version was only layer 1, and an assistant ran a homophonic solver on
it in nine commands. Layer 2 stops that: neighbouring tokens in the file are no
longer neighbouring letters, so quadgram scoring finds nothing.

## Intended solve

- **See the shuffle.** The punctuation tokens were transposed along with
  everything else. `<}>` comes *before* `<{>` in the file, and the flag's `<_>`
  are scattered all over it. Something reordered the tokens, and no key is
  needed to put them back.
- **Undo the columns.** Try each width `W`: rebuild the rows (column `c` holds
  rows `0, 1, 2, ...` at position `c`) and look at the punctuation. Only `W = 17`
  puts `<{> ... <_> ... <}>` together at the very end, like a flag. (Another
  check: tokens that are neighbours in the plaintext sit about 44 apart in the
  file, the number of rows. An "every 44th token" skip is close but drifts at
  each column boundary. It has to be columns.)
- **Solve the homophonic substitution.** Simulated annealing over token→letter
  maps, scored on English quadgram statistics within the runs between the
  literal tokens, with a light penalty for letter counts far from English. It
  gets the text readable but not perfect: a letter with a single token (`k`,
  `x`, ...) can come out as a common one. Read it and fix those
  (`nesttoeachother` → `next to each other`).

[`solve.py`](solve.py) does all of it with no key: it finds the width from the
punctuation, then anneals. It needs English quadgram counts, one `QUAD COUNT`
per line (`english_quadgrams.txt` from practicalcryptography.com, or counts
built from any big English text), and takes about half a minute:

```bash
python3 solve.py english_quadgrams.txt
# widths that rebuild a flag-shaped ending: [17]
# ...sothelettersthatstandnesttoeachotherinthelanguage...
# flag (fix the odd letter by reading): flag{seventeen_columns_and_many_masks}
```

[`decode.py`](decode.py) applies the real width and map (`../challenge/key.txt`)
and prints the exact plaintext, to check:

```bash
python3 decode.py
```

## Flag

```
flag{seventeen_columns_and_many_masks}
```

## Debrief: what you learn and how to protect against it

**What you learn:** two classical improvements on `mono` and why they still fail.
A homophonic substitution gives each letter several symbols, so the frequency
count is flat. A transposition moves the symbols around, so neighbouring symbols
are no longer neighbouring letters. Both are undone: the punctuation left in the
text reveals the column width, and the language's patterns (quadgrams) guide a
computer search to the substitution.

**The solve in short:**

1. Notice that the punctuation is out of order (`}` comes before `{`):
   something moved the tokens around.
2. Try each column width. Only 17 puts `{ ... _ ... }` together at the end.
3. With the order restored, run a search (simulated annealing) for the
   token-to-letter map that gives the most English-looking text.
4. Read the result and correct the few wrong letters by hand.

**How to protect against it:**

- Stacking classical tricks does not make a modern cipher. Language structure
  survives, and a laptop tries millions of keys per second.
- Small leaks break systems: the punctuation was left as it was "for
  readability", and that gave away the transposition. Encrypt the whole message,
  including its structure, and remember that length and format can leak too.
- Use AES-GCM or ChaCha20-Poly1305 from a standard library.

## How hard it is for an AI

A fresh assistant, given only `cipher.txt` and "What is the ctf flag?", spotted
the reordering from the punctuation. It modelled it as an "every 44th token" skip
instead of columns, so its (working) homophonic solver ran on a slightly wrong
order. After 25 tool calls it had no flag. The second paid hint names the
transposition exactly.

In a second test the assistant asked for a hint only once it stalled. It
stalled after 22 tool calls (a working homophonic solver, run on the shuffled
order), took hint 1 (30 points: the punctuation is out of order, and the shuffle
needs no key), and had the flag 4 calls later: it tried keyless reorderings,
kept the one that put `<{> ... <}>` in order, and found rows of 17 read by
columns. It never needed hint 2.

A 2026-11 re-test could not be completed: the subagent was stopped by a safety
classifier (a `[bio]` false positive, triggered somewhere in the substitution
plaintext or the n-gram scoring) before it finished, so there is no second clean
data point for mono-ai. Recorded per policy; not retried.

## Solving it with an AI (prompts)

Paste the contents of `cipher.txt` with the prompt.

- **Cold open:** "This is a cipher: one flat stream of space-separated tokens (mostly three-digit numbers, plus a few literal `<...>` tokens). It decrypts to English ending in a `flag{...}`. Work out the scheme and recover the plaintext."
- **When the punctuation looks shuffled:** "The `<...>` tokens are out of order, so the stream was transposed before you got it. Try a columnar transposition: for each width W, assume the tokens were written in rows of W and read off by columns; rebuild the rows and keep the W that puts `<{>`, the `<_>`s and `<}>` together at the end."
- **Then:** "Now it's a homophonic substitution with no word gaps. Write and run a solver: simulated annealing over token→letter maps, scored on English quadgrams within the runs between the literal tokens, with a small penalty for letter counts far from English."

## Hint pricing (2026-11)

Measured: in the baseline hint-on-stall test a stalled agent took hint 1 (then
30 pts) and solved **4 calls later** — the "the tokens were transposed before the
substitution" insight is most of the solve, so that hint was underpriced.
Re-priced on *cost ≈ (fraction of remaining work removed) × value* (value 450),
never lowering any cost:

| Hint | Removes | Cost |
|---|---|---|
| 1 — nudge (homophonic is the tool, but a reorder blocks it; punctuation is the clue) | the "why won't my solver converge" dead end | **40** (new rung) |
| 2 — the decisive reorder insight (keyless shuffle, punctuation out of order) | most of the remaining work (measured ≈4 calls to flag) | **90** (was the 30-pt hint) |
| 3 — exact transposition (rows of 17, read by columns) + the homophonic recipe | hands over the solve | **150** (was 70) |
