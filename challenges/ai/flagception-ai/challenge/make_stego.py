#!/usr/bin/env python3
"""Build the flagception-ai stego image: three layers, one per colour channel.

The original `flagception` / `image` / `birds` forensics tasks hide the flag
where `strings`, an EXIF viewer or a glance uncovers it. The first version of
this challenge used one textbook trick (blue-channel LSBs, zlib) on a cover an
AI could model pixel by pixel, so one prompt solved it. This one stacks three
layers, each in its own colour channel, and the first answer you find is a
decoy:

  1. "The dream" (blue LSBs, row-major, MSB-first): a 4-byte big-endian length
     and a zlib stream, the old challenge's exact layout. It inflates to a fake
     flag (DECOY) that CTFd rejects. A solver who stops here has to go back.
  2. "Limbo" (green LSBs, column-major: down column 0, then column 1, ...,
     MSB-first): a zip archive (PK..) holding limbo.txt with the real FLAG,
     encrypted with classic ZipCrypto. Its password is not in any wordlist, and
     the zip comment (readable without the password) says the totem opens it.
  3. "The totem" (red LSB plane): the password, drawn as white text on black.
     Invisible in the picture, but plain to read in a bit-plane viewer
     (Stegsolve, Aperi'Solve) or after rendering the plane yourself. No byte
     extraction finds it: it is a picture, so you have to look.

The cover is a Norwegian flag with a Droste effect (a flag inside a flag inside
a flag) plus film grain, so every LSB plane is noise to begin with and nothing
can be found by predicting the cover and diffing.

Needs Pillow (10.1 or newer, for the scalable default font).
Run:  python3 make_stego.py   -> writes ../distfiles/stego.png
"""
import math
import random
import struct
import zipfile
import zlib
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SEED = 20101607  # Inception's premiere, 16 July 2010
FLAG = b"flag{three_dreams_deep_in_limbo}"
DECOY = b"flag{you_are_still_dreaming}"
TOTEM = "the-top-keeps-spinning"  # zip password, drawn in the red LSB plane
ZIP_NAME = "limbo.txt"
ZIP_COMMENT = b"Limbo. The door opens only for your totem."
LIMBO_TEXT = b"You reached the bottom of the dream. Time for the kick.\n\n" + FLAG + b"\n"

UNIT = 32
W, H = 22 * UNIT, 16 * UNIT  # the Norwegian flag's 22:16 proportions, 704x512
RED, WHITE, BLUE = (190, 20, 50), (240, 240, 236), (18, 40, 104)

OUT = Path(__file__).resolve().parent.parent / "distfiles" / "stego.png"


# --- the cover ----------------------------------------------------------------

def norwegian_flag():
    img = Image.new("RGB", (W, H), RED)
    d = ImageDraw.Draw(img)
    d.rectangle([6 * UNIT, 0, 10 * UNIT - 1, H - 1], fill=WHITE)  # white cross
    d.rectangle([0, 6 * UNIT, W - 1, 10 * UNIT - 1], fill=WHITE)
    d.rectangle([7 * UNIT, 0, 9 * UNIT - 1, H - 1], fill=BLUE)  # blue cross
    d.rectangle([0, 7 * UNIT, W - 1, 9 * UNIT - 1], fill=BLUE)
    return img


def wave(img):
    """Darken the cloth in soft diagonal folds, so it looks less like a flat fill."""
    px = img.load()
    for y in range(H):
        for x in range(W):
            m = 0.84 + 0.16 * math.sin(2 * math.pi * (1.4 * x / W + 0.5 * y / H))
            r, g, b = px[x, y]
            px[x, y] = (round(r * m), round(g * m), round(b * m))
    return img


def droste(img, depth=5):
    """Put the whole picture, framed, inside the top-left canton, recursively."""
    cw = 6 * UNIT  # the canton is 6x6 units
    iw = cw - 16
    ih = iw * H // W
    x0, y0 = (cw - iw) // 2, (cw - ih) // 2
    for _ in range(depth):
        small = img.resize((iw, ih), Image.LANCZOS)
        framed = Image.new("RGB", (iw + 4, ih + 4), (60, 50, 40))
        framed.paste(small, (2, 2))
        img.paste(framed, (x0 - 2, y0 - 2))
    return img


def grain(img, rng):
    """Gaussian film grain: afterwards every bit plane 0 is noise."""
    px = img.load()
    for y in range(H):
        for x in range(W):
            px[x, y] = tuple(min(255, max(0, round(c + rng.gauss(0, 2.5)))) for c in px[x, y])
    return img


def make_cover(rng):
    return grain(droste(wave(norwegian_flag())), rng)


# --- layer 2: an encrypted zip, built by hand (zipfile cannot encrypt) -------

CRC_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0xEDB88320 if _c & 1 else _c >> 1
    CRC_TABLE.append(_c)


class ZipCrypto:
    """Traditional PKWARE encryption (APPNOTE 6.1), what `zip -e` writes."""

    def __init__(self, password):
        self.keys = [0x12345678, 0x23456789, 0x34567890]
        for byte in password:
            self._update(byte)

    @staticmethod
    def _crc(crc, byte):
        return (crc >> 8) ^ CRC_TABLE[(crc ^ byte) & 0xFF]

    def _update(self, byte):
        k0, k1, k2 = self.keys
        k0 = self._crc(k0, byte)
        k1 = ((k1 + (k0 & 0xFF)) * 134775813 + 1) & 0xFFFFFFFF
        k2 = self._crc(k2, k1 >> 24)
        self.keys = [k0, k1, k2]

    def encrypt(self, data):
        out = bytearray()
        for byte in data:
            t = (self.keys[2] | 2) & 0xFFFF
            out.append(byte ^ (((t * (t ^ 1)) >> 8) & 0xFF))
            self._update(byte)
        return bytes(out)


def encrypted_zip(rng):
    crc = zlib.crc32(LIMBO_TEXT)
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    deflated = comp.compress(LIMBO_TEXT) + comp.flush()
    # 12-byte encryption header: 11 random bytes, then the CRC's top byte as the
    # password check (general-purpose bit 3 is not set).
    header = bytes(rng.randrange(256) for _ in range(11)) + bytes([crc >> 24])
    body = ZipCrypto(TOTEM.encode()).encrypt(header + deflated)

    dos_time = (12 << 11) | (0 << 5) | 0  # 12:00:00
    dos_date = ((2010 - 1980) << 9) | (7 << 5) | 16  # 2010-07-16
    name = ZIP_NAME.encode()
    flags, method = 0x0001, 8  # encrypted, deflate
    local = struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, flags, method, dos_time, dos_date,
                        crc, len(body), len(LIMBO_TEXT), len(name), 0) + name
    central = struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, (3 << 8) | 20, 20, flags, method,
                          dos_time, dos_date, crc, len(body), len(LIMBO_TEXT), len(name),
                          0, 0, 0, 0, 0o100644 << 16, 0) + name
    cd_offset = len(local) + len(body)
    eocd = struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, 1, 1, len(central), cd_offset,
                       len(ZIP_COMMENT)) + ZIP_COMMENT
    return local + body + central + eocd


# --- embedding ----------------------------------------------------------------

def bits_of(data):
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def embed(px, channel, coords, data):
    bits = list(bits_of(data))
    if len(bits) > len(coords):
        raise SystemExit("cover too small for payload")
    for (x, y), bit in zip(coords, bits):
        p = list(px[x, y])
        p[channel] = (p[channel] & ~1) | bit
        px[x, y] = tuple(p)


ROW_MAJOR = [(x, y) for y in range(H) for x in range(W)]
COLUMN_MAJOR = [(x, y) for x in range(W) for y in range(H)]


def totem_mask():
    """The red-plane drawing: a black card with the password in white."""
    box = (W - 440, H - 132, W - 24, H - 24)
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.text((box[0] + 20, box[1] + 12), "TOTEM", fill=255, font=ImageFont.load_default(size=30))
    d.text((box[0] + 20, box[1] + 54), TOTEM, fill=255, font=ImageFont.load_default(size=36))
    return box, mask.point(lambda v: 255 if v >= 128 else 0)


def main():
    rng = random.Random(SEED)
    img = make_cover(rng)
    px = img.load()

    # Layer 1, blue: the decoy, in the layout of the old challenge.
    decoy = zlib.compress(DECOY, 9)
    embed(px, 2, ROW_MAJOR, len(decoy).to_bytes(4, "big") + decoy)

    # Layer 2, green: the encrypted zip, column by column.
    archive = encrypted_zip(rng)
    embed(px, 1, COLUMN_MAJOR, archive)

    # Layer 3, red: the totem, drawn into bit plane 0.
    box, mask = totem_mask()
    m = mask.load()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            r, g, b = px[x, y]
            px[x, y] = ((r & ~1) | (1 if m[x, y] else 0), g, b)

    img.save(OUT, "PNG", optimize=True)  # PNG is lossless; JPEG would destroy the LSBs
    verify(archive)
    print(f"wrote {OUT.name}: {W}x{H}, decoy {4 + len(decoy)} B in blue, zip {len(archive)} B in green")


def verify(archive):
    """Round-trip every layer from the saved file."""
    img = Image.open(OUT).convert("RGB")
    px = img.load()

    def read(channel, coords, nbytes):
        bits = [px[x, y][channel] & 1 for x, y in coords[:nbytes * 8]]
        return bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8))

    head = read(2, ROW_MAJOR, 4)
    assert zlib.decompress(read(2, ROW_MAJOR, 4 + int.from_bytes(head, "big"))[4:]) == DECOY

    carved = read(1, COLUMN_MAJOR, W * H // 8)  # the whole plane: the zip plus trailing noise
    assert carved.startswith(archive)
    with zipfile.ZipFile(BytesIO(carved)) as z:
        assert z.comment == ZIP_COMMENT
        assert z.read(ZIP_NAME, pwd=TOTEM.encode()) == LIMBO_TEXT
        try:
            z.read(ZIP_NAME, pwd=b"wrong")
        except RuntimeError:
            pass
        else:
            raise AssertionError("zip opened without the right password")

    box, mask = totem_mask()
    m = mask.load()
    assert all(px[x, y][0] & 1 == (1 if m[x, y] else 0)
               for y in range(box[1], box[3]) for x in range(box[0], box[2])), "totem plane"
    assert FLAG not in OUT.read_bytes() and DECOY not in OUT.read_bytes()


if __name__ == "__main__":
    main()
