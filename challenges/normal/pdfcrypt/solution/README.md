# pdfcrypt — crack the PDF password

**Category:** forensics · **Flag:** `flag{kramer_the_best_hacker_ever}`

`encrypted.pdf` is a password-protected PDF. It uses the standard security handler
at **V 4 / R 4**, 128-bit, with the streams encrypted as **AESV2** (and the metadata
encrypted). The *password check* for R3/R4 is the usual MD5 + RC4 computation, so
`pdfcrack`, `john` and `hashcat` (mode 10500) all crack it the same way — AESV2 only
changes how the content is decrypted afterwards.

### Crack it

`pdfcrack` (from `apt install pdfcrack`) reads the encryption parameters and runs a
wordlist. The description says the password is common, so `rockyou.txt` is enough:

```bash
$ pdfcrack encrypted.pdf --wordlist=rockyou.txt
PDF version 1.6
Security Handler: Standard
V: 4
R: 4
P: -4
Length: 128
Encrypted Metadata: True
...
found user-password: 'hacked'
```

(A plain brute force without a wordlist works too but is far slower.)

Alternatively, extract the hash and use John/hashcat:

```bash
pdf2john encrypted.pdf > hash.txt
hashcat -m 10500 hash.txt rockyou.txt          # or: john --wordlist=rockyou.txt hash.txt
```

### Crack it without installing anything on your machine (Docker sandbox)

If you'd rather not install `pdfcrack`/`pdf2john` (or download `rockyou.txt`) onto
your own system, do the whole solve inside a throwaway container. This directory
ships a `Dockerfile` and `solve.sh` that bake in `pdfcrack`, `pdftotext` and the
wordlist, so the only thing that touches your host is a read-only bind mount of the
PDF:

```bash
# from the challenge folder (pdfcrypt/)
docker build -t pdfcrypt-solve solution/
docker run --rm -v "$PWD/distfiles:/work:ro" pdfcrypt-solve encrypted.pdf
```

```
[*] Cracking the open-password of encrypted.pdf with rockyou.txt...
[*] Password: hacked
[*] Flag:
flag{kramer_the_best_hacker_ever}
```

`docker rmi pdfcrypt-solve` afterwards and nothing is left behind. Building needs
network once (to fetch the tools and the wordlist); the run itself is offline. You
can mount your own list instead of rockyou with `-v /path/to/list.txt:/wordlist.txt`.

#### Or: a throwaway shell with the tools, to drive the solve by hand

If you want to run the cracking steps **yourself** (to learn, or experiment) rather
than have `solve.sh` do it, you don't need the `Dockerfile` at all. Launch a stock
Debian container, install the tools inside it, and bind-mount the folder that holds
your `encrypted.pdf` (e.g. your downloads) **read-only** at `/work`:

```bash
docker run --rm -it \
  -v "$HOME/Downloads:/work:ro" \
  debian:13-slim bash -c '
    apt-get update -qq &&
    apt-get install -y --no-install-recommends pdfcrack poppler-utils wget ca-certificates &&
    wget -qO /rockyou.txt https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt &&
    cd /work && exec bash
  '
```

(Adjust the `-v` source path to wherever the PDF is — on WSL that might be
`/mnt/c/Users/<you>/Downloads`.) This drops you into a shell in `/work` with
`pdfcrack`, `pdftotext` and `/rockyou.txt` ready. Then run the steps below by hand:

```bash
pdfcrack encrypted.pdf                 # inspect the encryption parameters (V, R, Length, AESV2)
pdfcrack -w /rockyou.txt encrypted.pdf # crack against the wordlist -> found user-password: 'hacked'
pdftotext -upw hacked encrypted.pdf -  # read the flag (note the trailing '-')
```

Because the mount is read-only and the container is `--rm`, nothing is written to
your host and the container vanishes on `exit`; `docker image rm debian:13-slim`
removes the base image too if you want zero trace.

**Two gotchas worth knowing:**

- **Run `pdfcrack` *with* `-w <wordlist>`.** Without it, `pdfcrack` falls back to
  incremental **brute force** (trying `Zqwj`, `BEZt`, `oSAY`, … in order), which is
  hopelessly slow here. The description's "pretty common" is the hint to use
  `rockyou.txt` — with `-w` the password drops out in seconds.
- **`pdftotext` needs a trailing `-`** to print to stdout. `pdftotext -upw hacked
  encrypted.pdf` (no final argument) tries to *write* `encrypted.txt` next to the
  PDF, which fails on a read-only mount (`Couldn't open text file 'encrypted.txt'`).
  The `-` makes it stream the text to your terminal instead.

### Without pdfcrack or pdf2john at all

You never actually need `pdf2john` — that only *extracts a hash* for John/hashcat.
To recover a weak **open-password** you only need (a) something to test a password
and (b) a wordlist. Tools you may already have do both:

- **`qpdf`** (pure shell loop — `qpdf` succeeds only on the right password):

  ```bash
  while IFS= read -r p; do
    qpdf --password="$p" --decrypt encrypted.pdf /dev/null 2>/dev/null && { echo "password: $p"; break; }
  done < rockyou.txt
  ```

- **Python + `pikepdf`** (`pip install pikepdf`), same idea:

  ```python
  import pikepdf
  for p in open("rockyou.txt", encoding="latin-1", errors="ignore"):
      p = p.rstrip("\n")
      try:
          pikepdf.open("encrypted.pdf", password=p).close(); print("password:", p); break
      except pikepdf.PasswordError:
          pass
  ```

Either way, once you have `hacked`, read the flag with `pdftotext -upw` as below.
And since the description says the password is *common*, a handful of manual guesses
(`pdftotext -upw <guess> …`) from a top-100 list finds it without any cracker.

### Read the flag

Open the PDF with the password `hacked`; the flag is in the **page text** (the
painting in the document is a decoy). Easiest from the terminal:

```bash
pdftotext -upw hacked encrypted.pdf - | grep -o 'flag{[^}]*}'
# flag{kramer_the_best_hacker_ever}
```

The trailing `-` is important: it sends the extracted text to stdout. Omit it and
`pdftotext` tries to *write* `encrypted.txt` beside the PDF instead (which fails on a
read-only mount with `Couldn't open text file 'encrypted.txt'`).

**Lesson:** a weak, common PDF open-password is crackable in seconds with a wordlist,
regardless of the AES content encryption behind it.

## Debrief: what you learn and how to protect against it

**What you learn:** encryption is only as strong as the password behind it. The
PDF uses AES, which nobody breaks, but the password is a common word, so a
wordlist attack (`rockyou.txt`) finds it in seconds. You also learn the standard
tools: `pdfcrack`, or `pdf2john` with John/hashcat.

**The solve in short:**

1. The PDF asks for a password, and the description says it is a common one.
2. Run a wordlist against it: `pdfcrack -w rockyou.txt encrypted.pdf` gives
   `hacked`.
3. Open the PDF with it and read the flag in the text:
   `pdftotext -upw hacked encrypted.pdf -`.

**How to protect against it:**

- Use a long, random password or passphrase from a password manager. Anything
  that is in a wordlist, or is a word plus a year, will be found.
- Choose AES-256 when you encrypt a PDF (PDF 2.0). It also makes each guess
  slower than the older 128-bit variants do.
- Send the password through another channel than the file, or better, share the
  document through a system with access control instead of a password-protected
  attachment.
