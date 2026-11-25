#!/usr/bin/env bash
# Build writeup.pdf from writeup.md (in this folder) in the "Illustrated" style.
# Requires: pandoc, pdflatex (TeX Live: texlive-latex-extra, texlive-fonts-extra,
# texlive-pictures, fontawesome5, plex, montserrat, frcursive, inconsolata, tcolorbox).
# Run: ./build.sh
set -euo pipefail
cd "$(dirname "$0")"
# let pdflatex (run by pandoc in a temp dir) find diagrams/*.tex
export TEXINPUTS="$(pwd)//:${TEXINPUTS:-}"
pandoc writeup.md \
  -o writeup.pdf \
  --pdf-engine=pdflatex \
  --lua-filter=style.lua \
  -H header.tex \
  -V documentclass=article \
  -V papersize=a4 \
  -V geometry:a4paper,margin=2cm,includehead,headsep=8pt \
  -V fontsize=10pt \
  -V colorlinks=true \
  -V linkcolor='[HTML]{0B6B61}' \
  -V urlcolor='[HTML]{B4481F}' \
  -V toccolor='[HTML]{26231D}'
echo "Wrote writeup.pdf"
