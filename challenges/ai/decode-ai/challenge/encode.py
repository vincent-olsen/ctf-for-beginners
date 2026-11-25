#!/usr/bin/env python3
"""decode-ai encoder (AI-modus).

The original decode1-3 challenges are nested encodings you peel with CyberChef's
"Magic" (base64 -> base32 -> ...). The first AI-modus version stacked nine
layers with a repeating-key XOR whose key rode inline (XORKEY=...|), and an
assistant peeled it in about two minutes: the inline marker told it which text
transform was right and handed it the key. So now:

  * No key in the stream. The XOR keys are recovered by known plaintext: under
    the XOR is gzip, and a gzip header (Python's, with mtime=0) is always
    1f 8b 08 00 00 00 00 00 02 ff. XOR its first 8 bytes with the ciphertext and
    out comes the 8-byte key; bytes 8 and 9 (02 ff) confirm it.
    (A draft had the ROT13 on the base64 text, where it leaves no trace: the
    only check was this gzip header, two layers down, and an assistant spent
    23 tool calls without trying the two together. On the hex layer the ROT13
    shows: the hex digits a-f come out as n-s.)
  * A decoy core, and a buried real one. The gzip data is TWO members: a first
    gzip member whose note ends with a fake flag (CTFd rejects it), and - behind
    it - the real member, XORed again with a second key. But the real member does
    NOT sit right at the first member's trailer: a run of random-looking filler
    comes first, so the leftover bytes read as undifferentiated junk. Applying
    the gzip-header trick at the boundary fails; you have to SLIDE it along the
    trailing bytes until the header signature appears, which is where the second
    member (and its key) begin. The filler is deterministic, so the committed
    blob is reproducible.

Encoding stack (top = applied first):
  1. the decoy note -> gzip                              = A
  2. the real note  -> gzip -> XOR with KEY2 (8 bytes)   = B
  3. A + PAD (random-looking filler) + B
  4. that -> repeating-key XOR with KEY1 (8 bytes, from the start)
  5. base64
  6. reverse the whole string
  7. hex encode
  8. ROT13 the letters (the hex digits a-f become n-s)
  9. base32 encode -> what the player receives

Run:  python3 encode.py   -> writes ../distfiles/encoded.txt
"""
import base64
import codecs
import gzip
import hashlib
import zlib
from pathlib import Path

FLAG = "flag{gz1p_h34d3rs_g4v3_up_b0th_k3ys}"
DECOY = "flag{th3_c0r3_1s_r34ch3d}"
KEY1 = b"\x8e\x21\x5c\xd3\x07\x9a\xf4\x66"
KEY2 = b"\x3b\xc9\x70\x1e\xa5\x52\x0d\xe8"
GZIP_HEADER = bytes.fromhex("1f8b08000000000002ff")  # gzip.compress(..., mtime=0)
PAD_LEN = 48  # filler before the second member, so it is not at the boundary

DECOY_NOTE = (
    "Peeling notes, entry the eighth.\n"
    "You made it to the core. Nothing lies beneath this layer; what trails it is\n"
    "only padding, and padding keeps no secrets.\n"
    "The vault phrase is " + DECOY + "\n"
)
REAL_NOTE = (
    "Peeling notes, entry the ninth.\n"
    "Nobody slides the header trick past the padding. You did.\n"
    "The vault phrase is " + FLAG + "\n"
)


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _pad(n: int) -> bytes:
    """Deterministic pseudo-random filler. Reproducible (so the committed blob
    never changes) but uniformly random-looking, so the second member's start is
    not an obvious boundary in the trailing bytes."""
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(b"decode-ai pad v1\x00" + counter.to_bytes(4, "big")).digest()
        counter += 1
    return bytes(out[:n])


def encode() -> str:
    a = gzip.compress(DECOY_NOTE.encode(), 9, mtime=0)             # 1
    b = _xor(gzip.compress(REAL_NOTE.encode(), 9, mtime=0), KEY2)   # 2
    raw = _xor(a + _pad(PAD_LEN) + b, KEY1)                         # 3, 4
    s = base64.b64encode(raw).decode()                             # 5
    s = s[::-1]                                                    # 6
    s = s.encode().hex()                                           # 7
    s = codecs.encode(s, "rot13")                                  # 8
    return base64.b32encode(s.encode()).decode()                   # 9


def find_gzip_member(data: bytes, start: int = 0):
    """Slide the known-plaintext check along the bytes: the (offset, 8-byte key)
    where a gzip header (1f8b...02ff) appears XORed into the data. The first hit
    from `start` wins. None if there is none."""
    for off in range(start, len(data) - 9):
        key = _xor(data[off:off + 8], GZIP_HEADER[:8])
        if _xor(data[off + 8:off + 10], key[:2]) == GZIP_HEADER[8:10]:
            return off, key
    return None


def decode(blob: str):
    s = codecs.decode(base64.b32decode(blob).decode(), "rot13")    # 9', 8'
    raw = base64.b64decode(bytes.fromhex(s).decode()[::-1])        # 7', 6', 5'
    _off0, key1 = find_gzip_member(raw)                            # first member is at 0
    d = zlib.decompressobj(31)                                     # 31: gzip
    decoy = d.decompress(_xor(raw, key1)) + d.flush()
    rest = d.unused_data                                           # PAD + the second member
    off, key2 = find_gzip_member(rest)                            # the second member, past the filler
    real = gzip.decompress(_xor(rest[off:], key2))                 # 2'
    return decoy.decode(), real.decode(), off


def main() -> None:
    here = Path(__file__).resolve().parent
    blob = encode()
    (here.parent / "distfiles" / "encoded.txt").write_text(blob + "\n")
    decoy, real, off = decode(blob)
    assert decoy == DECOY_NOTE and real == REAL_NOTE, "round-trip failed"
    assert off == PAD_LEN, f"second member found at {off}, expected {PAD_LEN}"

    # The whole point of the padding: the gzip-header trick applied AT the
    # boundary (offset 0 of the trailing bytes) must NOT find the second member.
    raw = base64.b64decode(bytes.fromhex(codecs.decode(
        base64.b32decode(blob).decode(), "rot13")).decode()[::-1])
    d = zlib.decompressobj(31)
    d.decompress(_xor(raw, KEY1))
    rest = d.unused_data
    assert find_gzip_member(rest, 0)[0] == PAD_LEN, "member should be behind the filler"
    assert _xor(rest[:2], _xor(rest[:8], GZIP_HEADER[:8])[:2]) != GZIP_HEADER[8:10], \
        "the trailing bytes must NOT read as gzip at the boundary"

    try:
        gzip.decompress(_xor(raw, KEY1))
    except gzip.BadGzipFile:
        pass  # good: the plain decompress stops at the first member's trailer
    else:
        raise AssertionError("the padded second member should not decompress plainly")

    print("layers: base32, ROT13, hex, reverse, base64, XOR (key from the gzip header), gzip, "
          "then PAD filler, then behind it: XOR (second key) + gzip")
    print("blob length:", len(blob), " second member at offset", off, "of the trailing bytes")
    print("decoy:", DECOY, " real:", FLAG)


if __name__ == "__main__":
    main()
