# Self-contained cracker for pdfcrypt.
#
# Everything the solve needs — pdfcrack, the rockyou wordlist, and pdftotext —
# is installed INSIDE this image. You run it against the PDF with a bind mount,
# so nothing is ever installed on your own machine; delete the image afterwards
# and no trace is left on the host.
#
#   docker build -t pdfcrypt-solve solution/
#   docker run --rm -v "$PWD/distfiles:/work:ro" pdfcrypt-solve encrypted.pdf
#
# Building needs network once (to apt-get the tools and fetch rockyou). After
# that the container runs fully offline.
FROM debian:13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      pdfcrack poppler-utils ca-certificates wget \
 && rm -rf /var/lib/apt/lists/*

# rockyou.txt — the classic "common passwords" list (~133 MB). Stable mirror.
# Override at build time with --build-arg WORDLIST_URL=... if you prefer another.
ARG WORDLIST_URL=https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
RUN wget -qO /rockyou.txt "$WORDLIST_URL"

COPY solve.sh /usr/local/bin/solve
RUN chmod +x /usr/local/bin/solve

WORKDIR /work
ENTRYPOINT ["solve"]
