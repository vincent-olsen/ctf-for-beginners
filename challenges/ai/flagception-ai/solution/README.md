# flagception-ai (AI-modus)

`flagception`, `image` and `birds` hide the flag somewhere `strings`, `exiftool`,
or just looking will reveal. The first version of this challenge was one textbook
trick (blue-channel LSBs, zlib-compressed) on a cover an AI could predict pixel by
pixel, and one easy prompt solved it. This version is a flag inside a flag inside
a flag: three layers, one per colour channel, and the first flag you find is a
decoy.

`distfiles/stego.png` is a waving Norwegian flag with a smaller copy of itself in
the corner (a Droste effect), plus film grain. The grain makes every bit plane
noise to begin with, so you cannot find the payload by predicting the cover and
diffing.

| Layer | Where | What |
|---|---|---|
| 1, the dream | blue LSBs, row-major, MSB-first | 4-byte big-endian length + zlib: `flag{you_are_still_dreaming}`, a **decoy** |
| 2, limbo | green LSBs, **column-major** (down column 0, then column 1, ...), MSB-first | a ZipCrypto-encrypted zip with `limbo.txt`; its comment says *the door opens only for your totem* |
| 3, the totem | red LSB plane, as a **picture** | the zip password drawn as text: `the-top-keeps-spinning` |

## Intended solve

1. **The quick win is a trap.** `zsteg stego.png` (or any blue-LSB script) finds
   `zlib: data="flag{you_are_still_dreaming}"`. CTFd rejects it, and the text says
   why: you are still dreaming.
2. **Sweep every channel and order.** Plain `zsteg` reads row by row only;
   `zsteg -a stego.png` also reads column by column and reports
   `b1,g,lsb,yx .. file: Zip archive data`. Extract it with
   `zsteg -E b1,g,lsb,yx stego.png > limbo.zip` (the trailing noise after the zip
   doesn't bother `unzip`). It is encrypted, and `unzip -z limbo.zip` shows the comment.
3. **Don't crack it, look.** The password is in no wordlist. Open the image in
   Stegsolve and step to *Red plane 0*, or upload it to Aperi'Solve: a black card
   in the noise reads **TOTEM / the-top-keeps-spinning**.
4. `unzip -P the-top-keeps-spinning limbo.zip` and read `limbo.txt`.

[`extract.py`](extract.py) does all four steps (needs Pillow). It writes the red
plane to `./red_plane.png` for you to look at:

```bash
python3 extract.py     # reads ../distfiles/stego.png
```

The image is rebuilt from [`../challenge/make_stego.py`](../challenge/make_stego.py)
(deterministic; it round-trips every layer after writing).

## Flag

```
flag{three_dreams_deep_in_limbo}
```

The decoy `flag{you_are_still_dreaming}` is not accepted.

## Debrief: what you learn and how to protect against it

**What you learn:** LSB steganography: data hidden in the least significant bit of
each pixel's colour value, which the eye cannot see. You learn that every colour
channel and read order has to be checked, that a bit plane can be viewed as a
picture, and that the first thing a tool finds may be a decoy. It also shows that
an encrypted zip is no stronger than the place its password is kept.

**The solve in short:**

1. `zsteg stego.png` finds a flag in the blue channel. CTFd rejects it: a decoy.
2. `zsteg -a` also reads column by column and finds a zip archive in the green
   channel. Extract it. It is password-protected.
3. View the lowest bit of the red channel as an image (Stegsolve, Aperi'Solve):
   it shows the password as text.
4. Unzip with that password and read the flag.

**How to protect against it:**

- Steganography hides data, it does not protect it. Whoever knows where to look
  reads it. Secrets need encryption with a key that is stored somewhere else;
  here the key is in the same file as the lock.
- For defenders, the concern is data leaving (or malware entering) inside
  harmless-looking images. Re-encoding, resizing or recompressing uploaded and
  outgoing images destroys the lowest bits. Detection alone is unreliable.
- If you do use zip encryption, choose AES-256 (7-Zip) with a long random
  password. The old ZipCrypto has known weaknesses.

## How hard it is for an AI

A fresh assistant, given only the photo and the same one-line prompt that solved
the first version ("there should be a flag within this photo, can you help me
find it?"), found the decoy first. It then took 16 tool calls and five dead ends
to reach the real flag. It got the password from the bit planes before it found
the zip.

A 2026-11 re-test found it harder: a different fresh assistant found the blue
decoy and even recovered the red-plane password (`the-top-keeps-spinning`), but
did not crack the green-channel ZipCrypto layer within ~31 tool calls — it
reached the key insight (the password) but not the final decrypt. The step it
missed is reading the green LSB column-by-column as an encrypted zip; expect the
paid hint to carry weight here.

## Solving it with an AI (prompts)

Attach `stego.png` to an assistant that can run code (Python with Pillow).

- **Cold open:** "This PNG hides a flag. `strings` and `exiftool` find nothing. Find and extract it, and tell me how it was hidden."
- **After the decoy:** "That flag is wrong: it says I'm still dreaming. Check every colour channel's least-significant bits in both row-major and column-major order for file signatures (PK, zlib, PNG...)."
- **At the zip:** "The zip is password-protected and the comment mentions a totem. Render each colour channel's bit plane 0 as a black-and-white image so I can look at it."

## Hint pricing (2026-11)

Measured (hint-on-stall, fresh agent): a solver that had already found the decoy
and the red-plane totem password but was treating the green plane as "encrypted
noise" (reading it row-major) took the (then 30-pt) "sweep row **and** column"
hint and **solved 4 calls later** — reading green column-major reveals the ZIP.
That direction insight was the decisive step, so at 30 pts it was underpriced.
Re-priced (value 450), never lowering:

| Hint | Removes | Cost |
|---|---|---|
| 1 — nudge (the first flag is a decoy; more than one layer / channel, keep digging) | the "am I done?" dead end only | **30** (new rung) |
| 2 — it's a password-protected zip; the password is in the bit planes, don't crack it | a wrong rabbit hole (brute-forcing the password) | **60** |
| 3 — sweep every channel row **and** column (zsteg -a) | the decisive direction insight (measured +4 calls to flag) | **90** (was the 30-pt hint) |
| 4 — exact layout (blue decoy / green column-major zip / red totem) | hands over the solve | **150** |
