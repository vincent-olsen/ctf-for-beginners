# image — text hidden at the end of a JPEG

**Category:** forensics · **Flag:** `flag{detective_sh4rk}`

The flag is appended as plain text after the end of the JPEG data, so image viewers
ignore it but it is still in the file. The description's "something about the
terminal" and the hint ("which animal says meow?") both point at `cat`.

### Solve

Print the file in a terminal:

```bash
cat image.jpg
```

You get a screen full of binary garbage, and the last line ends with the flag:
`flag{detective_sh4rk}`.

### If `cat` only shows `<BINARY>`

Some terminal setups replace `cat` with [`bat`](https://github.com/sharkdp/bat)
(an alias, common with Oh My Zsh or Homebrew setups). `bat` refuses to print binary
files and shows only a header:

```
─────┬──────────────────────────────
     │ File: image.jpg   <BINARY>
─────┴──────────────────────────────
```

Any of these gets past it:

```bash
command cat image.jpg               # skip the alias and run the real cat
\cat image.jpg                      # same, shorter
strings image.jpg | grep flag       # only the readable text, then filter
grep -a -o 'flag{[^}]*}' image.jpg  # -a: treat the binary file as text
tail -c 30 image.jpg                # the flag is the last bytes of the file
```

`strings`, `grep` and `tail` are also the cleaner way to do it in general, since
they don't fill the terminal with binary.

**Lesson:** files can carry extra data that the program that opens them never shows.
Look at the raw bytes (`cat`, `strings`, a hex viewer) as well as the picture.

## Debrief: what you learn and how to protect against it

**What you learn:** a file can hold more than the program that opens it shows. An
image viewer stops at the end of the JPEG data, so text appended after it is
invisible in the picture but still in the file. `strings`, `tail` and `grep -a`
look at the raw bytes.

**The solve in short:**

1. The picture itself shows nothing, so look at the bytes.
2. `strings image.jpg | grep flag` (or `cat image.jpg`, `tail -c 30 image.jpg`).
3. The flag is the last line of the file.

**How to protect against it:**

- The same trick is used to smuggle data out of a network or malware in. A
  service that accepts uploads should re-encode images (which drops everything
  outside the image data) and check the content, not the file extension.
- Before you publish a file yourself, remember that it can carry more than you
  see: metadata (EXIF with GPS position, author names) and leftover data. Strip
  it with `exiftool -all=` or export a clean copy.
