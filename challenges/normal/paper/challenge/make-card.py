#!/usr/bin/env python3
"""Build the printable card for the paper challenge.

Reads flag.txt next to this file and writes card.html: two A4 pages. Page 1 is
the front, one A5 card (148 x 210 mm) in the middle with crop marks at its
corners, carrying the flag as text and as a QR code. Page 2 is the back, in the
same place and without the flag, for a two-sided print. Needs `pip install qrcode`.

    python3 make-card.py
    chromium --headless --no-pdf-header-footer --print-to-pdf=paper-flag.pdf card.html

Print paper-flag.pdf on A4, two-sided, at 100 % ("actual size", not "fit to page"), cut
along the crop marks and hide the card before the event starts.
"""
import html
from pathlib import Path

import qrcode

HERE = Path(__file__).resolve().parent
flag = (HERE / "flag.txt").read_text(encoding="utf-8").strip()

qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
qr.add_data(flag)
qr.make(fit=True)
matrix = qr.get_matrix()
cells = "".join(f"M{x} {y}h1v1h-1z" for y, row in enumerate(matrix) for x, on in enumerate(row) if on)
qr_svg = (f'<svg class="qr" viewBox="0 0 {len(matrix)} {len(matrix)}" shape-rendering="crispEdges">'
          f'<path d="{cells}"/></svg>')

page = (HERE / "card.template.html").read_text(encoding="utf-8")
page = page.replace("{{FLAG}}", html.escape(flag)).replace("{{QR}}", qr_svg)
(HERE / "card.html").write_text(page, encoding="utf-8")
print("wrote card.html")
