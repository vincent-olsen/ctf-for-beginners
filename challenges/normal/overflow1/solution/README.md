# Write-up — overflow1

**The overflow series (1 → 2 → 3).** Three challenges, the same bug each time,
with one new twist added at every step. overflow1 teaches the core idea; overflow2
adds a value you must *not* break; overflow3 adds a value you must hit *exactly*.
Solve them in order.

## The bug

The program reads your name into a 16-byte buffer, but tells `fgets` it may write
up to 32 bytes:

```c
struct { char name[16]; int points; } u;   // points sits right after name
u.points = 10;
fgets(u.name, 32, stdin);                   // BUG: name is only 16 bytes
if (u.points > 9000) print_flag();
```

The second argument to `fgets` is supposed to be the size of the destination
buffer. Here it is `32`, but `name` only has room for `16`. So if you type more
than 16 characters, the extra bytes don't just vanish — they are written into the
memory that comes *right after* `name`, and that memory is `points`.

## Memory layout

Local variables in a struct are laid out next to each other:

```
offset:  0                15 16             19
        [ name (16 bytes)   ][ points (4 bytes) ]
         ^ your input starts here
```

Your first 16 bytes fill `name`. Bytes 17–20 land on top of `points`.

## Solve

Send 20 characters: 16 to fill the buffer, 4 more to overwrite `points`.

```bash
python3 -c "print('A'*20)" | nc <host> <port>
```

The four `A`s that spill over set `points` to `0x41414141` = `1094795585`
(`A` is `0x41`), which is comfortably over `9000`, so the flag prints:

```
You have 1094795585 points
flag{m4king_an_OF_1s_h4rd}
```

**Idea to carry forward:** writing past the end of a buffer overwrites whatever
variable sits next to it in memory. overflow2 puts something in the way.

## Debrief: what you learn and how to protect against it

**What you learn:** the basic idea of a buffer overflow. A program writes more
bytes into a buffer than it has room for, and the extra bytes land in whatever
is stored next to it. Here that is the `points` variable, so by typing a long
name you change a value you were never supposed to control.

**The solve in short:**

1. Read the source: `name` is 16 bytes, but `fgets` is allowed to write 32.
2. `points` is stored right after `name`.
3. Send 20 characters: 16 fill `name`, 4 overwrite `points` with a large number.
   `python3 -c "print('A'*20)" | nc <host> <port>`.

**How to protect against it:**

- Give the real buffer size: `fgets(u.name, sizeof(u.name), stdin)`. A size
  typed in by hand is how this bug appears.
- Build with warnings and hardening on (`-Wall`, `-D_FORTIFY_SOURCE=2`). The
  compiler can see that 32 is larger than 16. This challenge is built with the
  protections turned off on purpose.
- Test with AddressSanitizer (`-fsanitize=address`) and fuzzing.
- Note that a stack canary does **not** catch this one: the overflow stays
  inside the struct and never reaches the return address. Only correct bounds
  (or a memory-safe language such as Rust or Go) fix it.
