## Challenge: Binary2 – Hitting the Guard Byte

In this challenge you don’t need to calculate an address difference like last time.  
Instead, you need to **enter the exact number of bytes** so your input reaches the guard byte.

When you connect to the service (or run the binary), it simply asks for input:

```
Enter your input:
```

It tells you how many bytes you sent and teases the `flag{` opening, but it only
hands over the real flag once you land on the exact length that flips the guard
byte.

### Rules
- **< 5 bytes** → nothing happens
- **5–23 bytes** → the guard is untouched; you just see the `flag{...` teaser and "Keep going..."
- **24 bytes** → the guard flips, and you get the full flag
- **> 24 bytes** → you overshoot, no flag

### How to Solve
Type a string of exactly 24 characters (since each ASCII character = 1 byte).  
For example:

```bash
$ ./binary
Enter your input: AAAAAAAAAAAAAAAAAAAAAAAA
You entered: 24 bytes
Leaked: flag{...

Nice! You found the required amount of bytes and overflowed the guard.

Correct! Here is your flag:
flag{Lift_Magic_Machine}
```

### Takeaway
- 1 character of input = 1 byte written to memory
- The guard byte sits immediately after the 24-byte buffer
- Reaching it requires exactly 24 characters of input

## Debrief: what you learn and how to protect against it

**What you learn:** one character of input is one byte in memory, and a buffer has
a fixed size. `strcpy` copies the input plus a terminating zero byte, so 24
characters fill the 24-byte buffer completely and the zero byte lands on the
byte right after it (the guard). (Retired for the
current event: the `overflow` series covers it.)

**The solve in short:**

1. Send input of different lengths and watch the program report how many bytes
   it got.
2. Find the length where the guard changes: exactly 24 characters.
3. Send 24 characters, e.g. `python3 -c "print('A'*24)" | nc <host> <port>`.

**How to protect against it:**

- Leave room for the terminating zero byte: a 24-byte buffer holds 23
  characters. The length check here accepts 24, one too many.
- Avoid `strcpy`. Copy with the destination's size as the limit, e.g.
  `snprintf(buf, sizeof(buf), "%s", input)`.
- Turn on compiler warnings and the standard hardening (`-Wall`,
  `-D_FORTIFY_SOURCE=2`, `-fstack-protector-strong`) and test with
  AddressSanitizer, which reports a write one byte past a buffer.
- Languages with bounds checking (Rust, Go, Java, Python) make this class of bug
  impossible or turn it into a clean error.
