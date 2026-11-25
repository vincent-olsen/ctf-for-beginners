#!/usr/bin/env python3
"""Solve flagception-ai, layer by layer. Needs Pillow. Reads ../distfiles/stego.png.

  1. Blue LSBs, row-major: [4-byte length][zlib] -> a decoy flag ("still dreaming").
  2. Sweep every channel and pixel order for a known file signature: the green
     LSBs, read column by column, start with PK\\x03\\x04, an encrypted zip.
  3. The zip's password is drawn in the red LSB plane: this script saves that
     plane as red_plane.png. Look at it (it reads "TOTEM the-top-keeps-spinning").
  4. Unzip limbo.txt with that password.

Usage:  python3 extract.py [password]
"""
import io
import sys
import zipfile
import zlib
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
img = Image.open(HERE.parent / "distfiles" / "stego.png").convert("RGB")
w, h = img.size
px = img.load()

ORDERS = {
    "row-major": [(x, y) for y in range(h) for x in range(w)],
    "column-major": [(x, y) for x in range(w) for y in range(h)],
}


def lsb_bytes(channel, order):
    bits = [px[x, y][channel] & 1 for x, y in ORDERS[order]]
    return bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits) - 7, 8))


# 1) The shallow layer: what the old challenge held.
blue = lsb_bytes(2, "row-major")
length = int.from_bytes(blue[:4], "big")
print("1) blue, row-major:", zlib.decompress(blue[4:4 + length]).decode(), " <- a decoy, CTFd rejects it")

# 2) Sweep: 3 channels x 2 orders, looking for file signatures.
SIGNATURES = {b"PK\x03\x04": "zip", b"\x78\xda": "zlib", b"\x89PNG": "png", b"\x1f\x8b": "gzip"}
archive = None
for ch, name in enumerate("RGB"):
    for order in ORDERS:
        data = lsb_bytes(ch, order)
        for magic, kind in SIGNATURES.items():
            if data.startswith(magic) or data[4:].startswith(magic):
                print(f"2) {name} LSBs, {order}: looks like {kind}")
                if kind == "zip":
                    archive = data

zf = zipfile.ZipFile(io.BytesIO(archive))  # trailing noise after the zip is fine
print("   zip holds", zf.namelist(), "comment:", zf.comment.decode())

# 3) The totem: render the red bit plane and look at it.
plane = Image.new("L", (w, h))
plane.putdata([255 * (px[x, y][0] & 1) for y in range(h) for x in range(w)])
plane.save("red_plane.png")  # in the current directory
print("3) saved the red LSB plane as ./red_plane.png: read the totem off it")

# 4) Unzip.
password = (sys.argv[1] if len(sys.argv) > 1 else "the-top-keeps-spinning").encode()
print("4)", zf.read("limbo.txt", pwd=password).decode())
