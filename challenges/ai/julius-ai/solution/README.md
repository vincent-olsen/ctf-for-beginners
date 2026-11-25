# julius-ai (AI-modus)

The original `julius` is a Caesar cipher: one fixed shift, brute-forceable in 25
tries. The first AI-mode version was Vigenère with the 8-letter key `AUGUSTUS`,
and an assistant broke it in two commands, since a short key repeats and Kasiski /
index of coincidence count the repeats. This version is a **running-key cipher**.
It is still Vigenère addition (A=0 ... Z=25), but the key is a text as long as the
message, so it never repeats.

The key is Caesar's own *Commentarii de Bello Gallico*, book I, chapter 1, letters
only. It starts mid-chapter, at *"Horum omnium fortissimi sunt Belgae..."*, not at
the famous *"Gallia est omnis divisa"*. The ciphertext is written the classical way,
in five-letter groups of capitals, so word lengths, case and punctuation give no
cribs. Only the flag at the end keeps its braces and underscores. They use no key.

`distfiles/cipher.txt`:

```
ACKBQ QUCPY DTTWB KWGND WEYLH VFCUK IBPGX GKCIS XCTWI PUYTZ
...
RYUXF IHGJU ZODSL PKYXU BAENT XDIHL PIZUJ CHKMJ
RLNO{SNZ_TTYY_LM_GAG_EQY}
```

## Intended solve

1. **Kasiski and IoC find nothing.** The index of coincidence is about 0.04 (random
   text) for every key length. There is no period. Not a repeating key.
2. **Crib the end.** `RLNO` must be `FLAG`. Guess the words before it, for
   example `...FORTHEARCHIVEIS`. Subtracting the guess gives the key at that spot:
   `SPROELIISCUMGERMANI`, which is Latin (*"...s proeliis cum Germani(s)..."*).
   In a Caesar challenge, that is *De Bello Gallico*.
3. **Find the starting point.** Take book I chapter 1 (for example from
   [the Latin Library](https://www.thelatinlibrary.com/caesar/gall1.shtml)), keep
   its letters, slide it along the ciphertext and subtract. At one offset (from
   *"Horum omnium"*, letter 226) the whole message turns into English. The crib in
   step 2 tells you where that is: the key under the flag must line up with
   *proeliis cum Germanis*.

Editions spell some words differently (`divisa`/`diuisa`, `provinciae`/`prouinciae`).
If a few letters decrypt wrong, look for a `u` where this key has a `v`.

[`solve.py`](solve.py) shows each step: the flat IoC, both cribs, and the
offset search:

```bash
python3 solve.py            # reads ../distfiles/cipher.txt
```

The plaintext ends with:

```
...COUNTALLYOULIKEMYSEALFORTHEARCHIVEISFLAG{ALL_GAUL_IS_THE_KEY}
```

## Flag

```
flag{all_gaul_is_the_key}
```

(CTFd flags are case-insensitive, so the upper-case form is accepted too.)

## Debrief: what you learn and how to protect against it

**What you learn:** the running-key cipher, and crib dragging. A key that is as
long as the message and never repeats defeats the usual statistics (Kasiski,
index of coincidence). It is still broken, because the key is ordinary text:
guess a piece of the plaintext, subtract it, and readable key text falls out.
From there you can find the book the key was taken from.

**The solve in short:**

1. Test for a repeating key: no period, so it is not a normal Vigenère.
2. Use what you know: the last group `RLNO{` must be `FLAG{`, and the words
   before it are guessable.
3. Subtract the guess from the ciphertext. The key at that position reads as
   Latin (`...PROELIIS CUM GERMANI...`).
4. Recognise Caesar's *De Bello Gallico*, take the chapter's letters and slide
   them along the ciphertext until the whole message becomes English.

**How to protect against it:**

- A key must be random. A key taken from a book, a song or a sentence has the
  statistics of language and can be guessed or found. Generate keys with a
  cryptographically secure random generator.
- Assume the attacker knows part of the plaintext (formats, greetings, headers).
  Modern ciphers are designed to stay secure against that.
- Use AES-GCM or ChaCha20-Poly1305 from a standard library. A true one-time pad
  needs a random key as long as the message, used once, which is rarely
  practical.

## How hard it is for an AI

A draft that kept word lengths and capitals fell in three tool calls. It opened
"Gaius Julius Caesar", and the 5/6/6-letter capitalised words gave that away. The
crib showed "galliaestom...", and the assistant knew the rest by heart. The
five-letter groups and the mid-chapter start are there to take those shortcuts
away. With them, a fresh assistant given only `cipher.txt` and "What is the
ctf-flag?" needed 21 tool calls and about 12 minutes. It worked through autokey,
progressive and keyword variants and Mark Antony's speech before the `FLAG` crib
plus *De Bello Gallico* landed.

A 2026-11 re-test did not solve it: a different fresh assistant derived the
`M,A,N,I` key letters from the `flag{`→`RLNO{` crib but modelled the cipher as a
repeating-key Vigenère with the key "MANI", wrote the body off as random filler,
and never recognised the running key as *De Bello Gallico* — it reported a
garbage flag. So the solve is genuinely agent-dependent at the "identify the key
text as Caesar's own prose" step; a stalled solver would need the hint.

## Solving it with an AI (prompts)

Paste `cipher.txt` along with the prompt.

- **Cold open:** "Here is ciphertext from a classical cipher, in five-letter groups. The plaintext is English and ends with a flag in `flag{...}` form. Identify the cipher and break it."
- **When period analysis fails:** "The key never repeats, so treat it as a running-key cipher. `RLNO` is `FLAG`; guess the plaintext just before it and show me the key letters that gives. Do they look like a language you recognise?"
- **Once you see Latin:** "That is Caesar's De Bello Gallico, book I chapter 1. Slide its letters along the ciphertext, subtract (A=0), and print the offset that gives English and the flag."

## Hint pricing (2026-11)

Measured (hint-on-stall, fresh agent): a solver that had already deduced a
running-key cipher and the `MANI` key fragment but stalled on identifying the key
text took the (then 30-pt) first hint and **solved 5 calls later** — the hint's
"crib the flag, work out the key, does it look like a language?" nudge is what
surfaced the Latin and led to *De Bello Gallico*. So that hint was near-decisive,
not a mild nudge. Re-priced (value 400), never lowering:

| Hint | Removes | Cost |
|---|---|---|
| 1 — nudge (periodic attacks all fail; the key is as long as the message → a running key) | the "what cipher is this" dead end only | **30** (new rung) |
| 2 — crib the flag, derive the key, "does it look like a language?" | most of the remaining work (measured +5 calls to flag) | **90** (was the 30-pt hint) |
| 3 — the exact key text (*De Bello Gallico* I.1) + the mid-chapter slide | hands over the solve | **130** |
