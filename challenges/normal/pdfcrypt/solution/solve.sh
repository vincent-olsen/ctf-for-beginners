#!/bin/sh
# Crack the pdfcrypt PDF and print the flag, entirely inside the container.
# Usage (inside the image): solve [PDF]   (default: encrypted.pdf in /work)
set -eu

PDF="${1:-encrypted.pdf}"
[ -f "$PDF" ] || { echo "error: $PDF not found (mount distfiles at /work)"; exit 1; }

# Wordlist: the baked-in rockyou, or one you mounted at /wordlist.txt.
WORDLIST=/rockyou.txt
[ -f /wordlist.txt ] && WORDLIST=/wordlist.txt

echo "[*] Cracking the open-password of $PDF with $(basename "$WORDLIST")..."
PW="$(pdfcrack -w "$WORDLIST" "$PDF" | sed -n "s/.*found user-password: '\(.*\)'.*/\1/p")"
[ -n "$PW" ] || { echo "no password found in the wordlist"; exit 1; }
echo "[*] Password: $PW"

echo "[*] Flag:"
pdftotext -upw "$PW" "$PDF" - | grep -o 'flag{[^}]*}'
