# decode-ai (AI-modus)

`decode1`–`decode3` are nested encodings you peel with CyberChef's **Magic**. The
first AI-modus version stacked nine layers with a repeating-key XOR whose key
rode inline (`XORKEY=...|`), and an assistant peeled it in about two minutes:
the marker told it which text transform was right and handed it the key. Now
there is no key in the stream, and the first core you reach is a decoy.

`distfiles/encoded.txt` is one line of base32.

## The stack, outside in

| Layer | How you spot it / undo it |
|---|---|
| base32 | `A-Z2-7`, `=` padding |
| ROT13 | "hex" whose letters are `n-s` instead of `a-f` |
| hex | then decodes to text |
| reverse | base64-looking text with its `=` padding at the **front** |
| base64 | gives bytes that are no known format |
| XOR, 8-byte key | **Known plaintext.** Guess that gzip lies under it. Python writes every gzip header with `mtime=0` as `1f 8b 08 00 00 00 00 00 02 ff`. XOR the first 8 bytes with it to get the key. Bytes 8–9 coming out `02 ff` confirms it. |
| gzip | the **decoy**: "You made it to the core. Nothing lies beneath this layer… The vault phrase is `flag{th3_c0r3_1s_r34ch3d}`" |
| after the first member | `gunzip` says *trailing garbage ignored*, and Python's `gzip.decompress` raises — but the leftover bytes read as undifferentiated junk, because a run of **random-looking filler** sits between the decoy and the real member. The header trick applied at the boundary **fails**. **Slide** it byte by byte along the trailing bytes until the gzip signature (`02 ff` in bytes 8–9) appears: that offset is where the **second gzip member** and its own 8-byte key begin. |
| gzip | the real note and flag |

[`solve.py`](solve.py) walks it:

```bash
python3 solve.py     # reads ../distfiles/encoded.txt
```

## Flag

```
flag{gz1p_h34d3rs_g4v3_up_b0th_k3ys}
```

The decoy `flag{th3_c0r3_1s_r34ch3d}` is not accepted.

## Debrief: what you learn and how to protect against it

**What you learn:** two things on top of the encoding layers from `decode1`–`3`.
First, XOR with a short repeating key is broken by known plaintext: file formats
start with fixed header bytes, and header XOR ciphertext gives the key. Second, to
distrust the first answer: the first "core" is a decoy, and the real content sits
behind it, in a second gzip member hidden after filler bytes.

**The solve in short:**

1. Peel the readable layers: base32, ROT13, hex, reverse, base64.
2. The result is unknown bytes. Guess that gzip lies under an 8-byte XOR, and
   XOR the first 8 bytes with the standard gzip header to get the key.
3. Decompress: a note with a flag that CTFd rejects (the decoy).
4. Notice the trailing data after the first gzip member. Slide the same header
   trick along it until the gzip signature appears.
5. That offset gives the second key and the second member, which holds the real
   flag.

**How to protect against it:**

- Repeating-key XOR is not encryption. Any predictable plaintext (file headers,
  `{"`, `<?xml`) reveals the key. Use an authenticated cipher (AES-GCM,
  ChaCha20-Poly1305) with a random key and a new nonce for every message.
- For defenders: this is how payloads are smuggled past scanners. A tool that
  stops at the first gzip member, or ignores "trailing garbage", never sees the
  rest. Inspection has to handle the whole file, and strict parsers should
  reject files with data after the end.

## How hard it is for an AI

The inline-key version fell to an assistant in about two minutes. This one was
given twice to a fresh assistant with only `encoded.txt` and "What is the ctf
flag?", and neither run found the flag in a chat-sized budget (about 24 tool
calls). Both peeled the text layers quickly and then stalled on the XOR:

- The first run (ROT13 still on the base64 text, where it left no trace) tried
  gzip-header keys and ROT13, but never both together. ROT13 then moved to the
  hex layer, where it shows.
- The second run assumed the key would be printable text and never tried a file
  header as known plaintext.

So the free solve hinges on one idea: XOR with a random key, and a gzip header
underneath. The 30-point hint points straight at it, and the 80-point hint gives
the header. Expect most teams to buy the first hint.

A third run asked for a hint only once it stalled. It stalled after 18 tool
calls at the XOR layer, took hint 1 (30 points), and had the real flag 4 calls
later: it XORed the start of the bytes against common file headers and found
gzip, then repeated the trick on the 144 bytes after the first member. It
noticed the decoy and gave the real flag. It never needed hint 2.

A 2026-11 re-test reproduced the clean-run difficulty a fourth time: a fresh
assistant peeled all five text layers and round-trip-verified them, but
optimised its repeating-key XOR search for printable ASCII and so never
recognised the gzip stream underneath — no flag in ~37 tool calls. Consistent
with the hint-gated design: the free solve really does hinge on trying a file
header as known plaintext.

**Decoy hardened (2026-11).** The re-test also showed the decoy was passable on a
plain "incorrect" alone — a solver who reached the decoy, submitted it and got
rejected was then told "there's a second member" almost for free, because the
real member sat right at the first member's trailer (the same header trick, one
offset over). To justify the near-answer hint and make the second member genuinely
harder to spot, a run of deterministic random-looking **filler** now sits between
the two members, so the leftover bytes read as junk and the boundary header trick
fails; the solver has to realise the member is *behind* the filler and slide the
known-plaintext check along to find it. The intended solve ([`solve.py`](solve.py))
does exactly that; hint costs are unchanged (the near-answer hint now describes the
slide). Nothing was made easier.

A timed hint-on-stall re-test (2026-11) confirmed it stays hint-gated: a fresh
agent peeled cleanly to the XOR blob but failed clean (20 calls); with hint 1 it
ran an exhaustive XOR search and proved the plaintext isn't ASCII under any key
(34); with hint 2 it tried gzip as known plaintext but only at key lengths 1–6,
never the real 8-byte key, so it never recovered even the first member (44, not
solved). The exact-bytes H3 (150) — the 8-byte-key recovery plus the slide past
the filler — is genuinely load-bearing.

## Regenerating

`python3 ../challenge/encode.py` rewrites `distfiles/encoded.txt`
(deterministic) and checks the round trip.

## Solving it with an AI (prompts)

Paste `encoded.txt`.

- **Cold open:** "Peel this nested encoding and give me the flag. Show each layer."
- **At the XOR:** "The bytes after base64 are XORed with a key that isn't in the stream. Assume gzip underneath: Python's header is 1f8b08000000000002ff. Derive an 8-byte key from the first 8 bytes and check that bytes 8-9 come out 02 ff."
- **After the first flag is rejected:** "Use zlib.decompressobj(31) and look at unused_data after the first gzip member. It isn't a gzip member at the boundary — there's random filler first — so slide the header known-plaintext check along it until bytes 8–9 come out 02 ff, then decompress the member at that offset."

## Hint pricing (2026-11)

Measured: in the baseline hint-on-stall test a stalled agent took hint 1 (then
30 pts) and had the flag **4 calls later** — the "XOR with a file header as known
plaintext" idea is nearly the whole solve, so that hint was badly underpriced.
Re-priced on the rule *cost ≈ (fraction of remaining work removed) × value*
(value 450), never lowering any cost:

| Hint | Removes | Cost |
|---|---|---|
| 1 — nudge (stacked layers; it's XOR with an external key) | the "what kind of layer is this" dead end, but not the crack | **40** (new rung) |
| 2 — the decisive known-plaintext idea (guess a file header) | most of the remaining work (measured ≈4 calls to flag) | **90** (was the 30-pt hint) |
| 3 — exact gzip bytes + the second-member trick | hands over the solve | **150** (was 80) |

The new cheap nudge gives a stuck solver the XOR insight without the
known-plaintext trick, so the decisive step is paid for at rung 2, not rung 1.
