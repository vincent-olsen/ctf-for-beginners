# Write-up — overflow3

Part 3 of the overflow series (do overflow1 and overflow2 first). Same shape as
overflow2 — a guard you must preserve and a `points` you must set — but now
`points` has to equal an **exact** value, and hitting it forces you to deal with a
byte you can't normally type.

## What changed since overflow2

```c
struct { char name[16]; unsigned int guard; unsigned int points; } u;
u.guard  = 0x44414544;   // the bytes "DEAD"
u.points = 10;           // starts as 0x0000000A
fgets(u.name, 128, stdin);
if (u.guard == 0x44414544 && u.points == 2680) print_flag();   // exact, not ">"
```

Two differences from overflow2:
- the guard value is `0x44414544` = the ASCII bytes `DEAD`, and
- `points` must be **exactly 2680**, not just large.

## Writing 2680 as bytes

`2680` in hex is `0x00000A78`. Little-endian (low byte first, as in overflow2),
`points` must become these four bytes in memory:

```
78 0A 00 00
```

The awkward one is `0x0A`. `0x0A` is a **newline** — the Enter key. And `fgets`
stops reading the moment it sees a newline. So you cannot just type `0x0A` as the
second byte of your payload: `fgets` would treat it as "end of input" and stop
there, and everything after it would be ignored.

## The trick: let the Enter key be your `0x0A`

Two facts combine to solve this:

1. `points` already starts at `10` = `0x0000000A`, i.e. the bytes `0A 00 00 00`.
2. `fgets` **keeps** the newline that ends your input and writes it into the
   buffer, right after your last typed character.

So you type everything up to and including the low byte `0x78` (the character
`x`), and then your Enter key supplies the `0x0A` as the very next byte — exactly
where the second byte of `points` needs to be:

```
[ 16 bytes name ][ "DEAD" guard ][ 'x' = 0x78 ][ Enter = 0x0A ]
                                   points byte 0   points byte 1
```

After the write, `points` in memory is `78 0A 00 00`:
- byte 0 = `0x78` (your `x`)
- byte 1 = `0x0A` (the newline `fgets` kept)
- bytes 2–3 = `0x00` (the string terminator `fgets` adds, and the `00` already
  there from the initial `10`)

That reads back as `0x00000A78` = **2680**, while `guard` stays `DEAD`.

## Solve

`print` adds the trailing newline for you, so:

```bash
python3 -c "print('A'*16 + 'DEADx')" | nc <host> <port>
```

```
guard = 0x44414544
points = 2680
flag{of_1s_n4ughty_&&_s0_are_u}
```

> **Why this one is tricky:** "the Enter key is the last byte of my exploit" is a
> genuinely subtle idea for a first pwn. There is a paid hint for it, and it's
> worth walking players through live. It's also the payoff of the series: once you
> see input as raw bytes in memory — including the newline — overflows stop being
> magic.

**The series in one sentence:** overflow1 = overwrite the neighbour; overflow2 =
overwrite the neighbour while preserving a guard; overflow3 = … and land the
neighbour on an exact value, newline byte and all.

## Debrief: what you learn and how to protect against it

**What you learn:** to see input as raw bytes in memory. `points` must become
exactly 2680 (`0x00000A78`, stored as `78 0A 00 00`), and `0x0A` is the newline
that ends the input. The solution is to let the Enter key be that byte, since
`fgets` stores the newline too. It is the hardest of the three because you have
to combine little-endian, the value already in the variable and how `fgets`
behaves.

**The solve in short:**

1. Read the source: 16 bytes of `name`, the guard `DEAD`, then `points`, which
   starts at 10 (`0A 00 00 00`).
2. Work out the bytes needed: `78 0A 00 00`.
3. Send 16 fillers, `DEAD`, then `x` (`0x78`). The newline that ends the line
   lands on the second byte of `points`, and the rest is already zero.
   `python3 -c "print('A'*16 + 'DEADx')" | nc <host> <port>`.

**How to protect against it:**

- Same cause, same fix as `overflow1` and `overflow2`: pass `sizeof(u.name)` to
  `fgets`, and build with warnings, `-D_FORTIFY_SOURCE=2` and AddressSanitizer in
  testing.
- Don't count on "awkward" bytes to save you. Attackers routinely work around
  bytes they cannot send (newlines, zero bytes), exactly as you just did. An
  exploit being difficult is not a defence.
- Memory-safe languages (Rust, Go) check every write against the buffer's size.
