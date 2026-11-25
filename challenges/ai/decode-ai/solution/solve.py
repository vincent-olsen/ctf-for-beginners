#!/usr/bin/env python3
"""Peel decode-ai. Reads ../distfiles/encoded.txt.

1. base32 (A-Z, 2-7) gives "hex" whose letters run n-s instead of a-f: ROT13.
   Undo it, then hex: a base64-looking string with its "=" padding at the
   FRONT, so it was reversed. Reversed and decoded, it gives bytes that are no
   known format.
2. Those bytes are XORed. Guess what lies under them: gzip. Every gzip header
   that Python writes with mtime=0 is 1f8b08000000000002ff, so XOR the first 8
   bytes with it to get an 8-byte key, and check that bytes 8-9 come out 02 ff.
3. gunzip: a note with a flag. It's a decoy. The data does not end there, but the
   real second gzip member is NOT right at the first member's trailer: a run of
   random-looking filler comes first. Applying the header trick at the boundary
   fails. SLIDE it along the trailing bytes until the gzip signature appears -
   that offset is where the second member (and its own key) start. Then gunzip.
"""
import base64
import codecs
import zlib
from pathlib import Path

GZIP_HEADER = bytes.fromhex("1f8b08000000000002ff")


def xor(data, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def find_gzip_member(data, start=0):
    """Slide the known-plaintext check: the first (offset, 8-byte key) from
    `start` where a gzip header appears XORed into the data. None if none."""
    for off in range(start, len(data) - 9):
        key = xor(data[off:off + 8], GZIP_HEADER[:8])
        if xor(data[off + 8:off + 10], key[:2]) == GZIP_HEADER[8:10]:
            return off, key
    return None


blob = (Path(__file__).resolve().parent.parent / "distfiles" / "encoded.txt").read_text().strip()
layer = base64.b32decode(blob).decode()
print("after base32:", layer[:40], "...  (letters n-s: ROT13'd hex)")
text = bytes.fromhex(codecs.decode(layer, "rot13")).decode()
print("after ROT13 + hex:", text[:40], "...  (= at the front: reversed base64)")
raw = base64.b64decode(text[::-1])

_off0, key1 = find_gzip_member(raw)
print("XOR key from the gzip header:", key1.hex())

d = zlib.decompressobj(31)
first = d.decompress(xor(raw, key1)) + d.flush()
print("\nfirst gzip member:\n" + first.decode())

rest = d.unused_data
print(f"...and {len(rest)} bytes after it, starting {rest[:4].hex()}")
# The header trick AT the boundary misses - the real member is behind the filler.
if find_gzip_member(rest, 0)[0] != 0:
    print("no gzip header at the boundary; sliding along the trailing bytes...")
off, key2 = find_gzip_member(rest)
print(f"second member found at offset {off} (behind {off} filler bytes), key {key2.hex()}")
print(zlib.decompress(xor(rest[off:], key2), 31).decode())
