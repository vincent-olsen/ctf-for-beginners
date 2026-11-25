# pwn-ai (AI-modus)

The pwn family (`overflow1`–`overflow5`, `binary1`/`binary2`) had no AI-bracket
sibling — this is it. Where the beginner overflows just smash a local variable or
return straight to a `win`, this one needs a small **ROP chain**: `win()` prints
the flag only when called with the right argument, so you must control `rdi`
before returning into it.

Players get the exact `binary` (64-bit, no PIE, no canary, **stripped**); its
source `binary.c` is a paid hint, not a distfile. The flag lives on the server
**only in encrypted form** (`flag.enc`): there is no plaintext copy anywhere.
`win()` decrypts it with the key passed in `rdi`, so the argument is not a gate
you can jump past — the right value has to be in `rdi` for the decryption itself
to come out as the flag. The binary is stripped on purpose: with the
`win`/`gadget` symbols present, an AI read the whole plan straight off `nm`, so
the player now has to reverse the logic from the disassembly.

## The bug and the plan

`vuln()` does `read(0, buf, 256)` into a 64-byte buffer — a classic stack
overflow. `win(unsigned long key)` reads `flag.enc` and **XOR-decrypts it with a
keystream seeded by `key`**; only `key == 0xc0ffee` turns the ciphertext back
into the flag (any other value prints static). Nothing calls `win` normally. No
PIE means every address is static.

1. **Offset** to the saved return address is **72** bytes.
2. Set the argument: return into a `pop rdi ; ret` gadget, then the key.
3. Return into `win`.

Addresses (read from `objdump -d binary` / ROPgadget — the binary is stripped,
so there are no symbol names to go by; identify the functions by what they do):

```
win           0x4012b8   # reads flag.enc and decrypts it with the key in rdi
pop rdi; ret  0x4012b3   # the planted gadget
key           0xc0ffee   # the decryption key (visible: cmp rdi, 0xc0ffee)
```

Payload: `"A"*72 + p64(0x4012b3) + p64(0xc0ffee) + p64(0x4012b8)`.

The `0xc0ffee` key is still discoverable from the disassembly (`cmp rdi,
0xc0ffee` in `win`), so the challenge stays fair — but because `win` *uses* the
key as the decryption key rather than merely comparing it, returning past the
check to the printer yields garbage, not the flag. The `rdi` argument is
unavoidable.

## Run it

```bash
python3 exploit.py <host> <port>      # nc host/port from CTFd
python3 exploit.py --local ./binary   # against a local copy (needs flag.enc in cwd)
```

On the server, socat hands the binary a pty. socat itself clears flow control and
IEXTEN on it (`ixon=0,ixoff=0,iexten=0`) the instant you connect, and `start.sh`
then prints the AI-modus banner and puts the pty in fully raw input mode
(`stty -icanon -echo -isig -ixon -ixoff -iexten -icrnl -inlcr -igncr -istrip`)
before exec'ing the binary. Without that a cooked pty mangles the control bytes
in the chain (e.g. the 0x11 in the `pop rdi` gadget address `0x4011fe`), and it
arrives broken. The banner comes before the "Speak, friend" prompt, so
`exploit.py` waits for the prompt before sending.

The container listens once per AI-modus effects level the player picks on the
board: host port 1246 (level 2, the default), 1247 (-1, WEB 1.0), 1248 (3, AI
HORROR) and 1249 (1, CALM). Only the banner differs; the binary, the pty settings
and the solve are the same on every port, and no banner contains the word
"enter" that the exploit waits for.

Output ends with:

```
[+] correct key — the vault opens:
flag{ret2win_with_the_right_key_in_rdi}
```

Recognising "ret2win, but it takes an argument, so I need a `pop rdi` gadget" and
building the chain is the AI-tier step. `pwntools` makes it a five-liner
(`ROP(elf)`), and an assistant will lay out the chain from the source.

## Flag

```
flag{ret2win_with_the_right_key_in_rdi}
```

## Rebuilding

```bash
make -C challenge     # hardening-off like overflow1-3, but STRIPPED (-s, no -g)
```

Unlike the overflows, the `Makefile` builds this one stripped (`-s`, and no
`-g`): the named `win`/`gadget` symbols gave the ret2win away. The hardening-off
flags (`-fno-stack-protector -no-pie`) are untouched, and stripping removes only
the symbol table, so the static addresses are unchanged. Rebuilding can still
shift them; if you rebuild, re-read them from `objdump -d binary` and update the
payload. The committed `binary` matches the addresses above.

`make` also (re)generates `flag.enc` from `flag.txt` with `mkenc`, which shares
the stream cipher (`cipher.h`) the binary decrypts with, so the two can never
drift. `flag.enc` is what the container ships; the plaintext `flag.txt` stays in
the repo (source of truth + `tools/check-flags.py`) but is **not** copied into
the image. If you change the flag, re-run `make` and recommit `binary`,
`flag.enc` and `distfiles/binary`.

## How hard it is for an AI

With the symbols present, a fresh assistant with the binary and "What is the ctf
flag?" solved it in **4 tool calls** — it read `win`/`gadget`/`print_flag` off
`nm`/checksec and built the chain. After stripping, a fresh assistant solved it
in **6 tool calls** (~95 s): no symbols, so it had to disassemble and map the
functions (the 256-into-64 overflow, the `0xc0ffee` gate, the `pop rdi` gadget)
by behaviour before writing the exploit — real reversing rather than a symbol
read.

**The `rdi`-skip shortcut is now closed (2026-11).** In the earlier cut, `win`
merely compared the key and then read a plaintext `flag.txt`, so a solver could
return **past** the `key == 0xc0ffee` check — straight to the inner flag-printer —
and skip the argument entirely. Now the flag exists on the server only as
`flag.enc` and `win` *decrypts* it with the key in `rdi` (XOR keystream seeded by
the key, `cipher.h`); there is no plaintext copy and no address that prints the
flag without `0xc0ffee` in `rdi`. Verified: a wrong key, and returning directly
to the printer, both yield static, never the flag; only the full chain
(`pop rdi; 0xc0ffee; win`) works. So the "control `rdi`" argument is now
unavoidable, which is strictly harder than before.

A 2026-11 blind re-test after the change: a fresh zero-context assistant, given
only the stripped binary and the live `nc` service (black-box, no source), solved
it in **~5 tool calls**. It disassembled `win`, saw that the key passed in `rdi`
is **both** the XOR decryption key and the `0xc0ffee` gate check ("the same value
serves as both"), found the `pop rdi; ret` gadget, computed the 72-byte offset,
and sent `A*72 + pop_rdi + 0xc0ffee + win` over a raw socket — flag on the first
try, no pwntools. This is the point of the change: the intended ROP was always
the fast path, so closing the skip-the-argument shortcut does **not** slow the
clean solve (it stays ~5–6 calls, entry/mid tier), it only removes the cheaper
alternate route — the challenge is strictly not easier, and the `rdi` argument is
now genuinely unavoidable.

The flag string and the intended ROP are otherwise unchanged, so a solver who had
already found the clean chain is unaffected; only the skip-the-argument shortcut
is gone.

## Solving it with an AI (prompts)

Give it the binary and the nc host:port (and `binary.c`, if you bought the source hint).

- **Cold open:** "Attached is a 64-bit Linux binary (no PIE, no canary, stripped); it runs at `nc <host> <port>`. Exploit it to print the flag. Give me a pwntools script."
- **If it stalls:** "The vulnerable function reads 256 bytes into a 64-byte buffer. There's a function that prints the flag only when its first argument (`rdi`) is `0xc0ffee`, and nothing calls it normally. Build a ROP chain: 72 bytes of padding, then a `pop rdi ; ret` gadget (find it with ROPgadget), then `0xc0ffee`, then the address of that function. Write the pwntools exploit (use `ROP(elf)` and connect with `remote`)."
