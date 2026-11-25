# Write-up – overflow4

## Step 1 – Understanding the challenge
We are given a compiled binary that asks for input and has a hidden function that prints the flag.  
The goal is to figure out the **exact number of bytes** needed to set a guard byte (`key`) to `0x00`.  
From the README and challenge description, we know this is most likely done via a buffer overflow.

---

## Step 2 – Initial reconnaissance
We can run `strings` and `nm` on the binary to look for interesting symbols:
```bash
strings binary 
```
We find a function like `theres_is_a_specific_byte_size_to_hit_here_function` or similar, which is not called from `main()`.

---

## Step 3 – Static analysis with objdump
Instead of brute-forcing, we can use objdump to disassemble the binary:

```bash
objdump -d ./binary
```

Look at the function: `theres_is_a_specific_byte_size_to_hit_here_function`

Inside, we see:
```bash
401361: lea    rax,[rbp-0x40]   ; buffer start (buf)
...
401349: mov    BYTE PTR [rbp-0x9],0xff  ; guard byte
...
40137c: movzx  eax,BYTE PTR [rbp-0x9]   ; check guard
```

So:
* Buffer starts at [rbp-0x40]
* Guard is at [rbp-0x9]

## Step 4 – Calculating the distance
`(rbp - 0x9) - (rbp - 0x40) = 0x37 = 55 bytes`

This means entering exactly 55 characters will cause the NUL terminator from scanf to overwrite the guard.

## Step 5 – Exploiting
Send exactly 55 As to flip the guard:
```bash
python3 -c "print('A'*55)" | ./binary
```
On the remote challenge:
```bash
python3 -c "print('A'*55)" | nc <host> <port>
```

## Step 6 – Summary

* Vulnerability: off-by-one buffer overflow into a guard byte.
* Required input: 55 characters (no spaces).
* Result: NUL terminator overwrites key → guard becomes 0x00 → flag_function is called.

## Debrief: what you learn and how to protect against it

**What you learn:** an off-by-one overflow, and how to find distances in a binary
without the source. `scanf("%s")` writes the input plus a terminating zero byte.
With exactly 55 characters in a 55-byte buffer, that zero byte lands on the guard
right behind it. You also learn basic static analysis with `strings`, `nm` and
`objdump`. (Hidden in the current event.)

**The solve in short:**

1. Look at the binary: `strings binary`, `objdump -d ./binary`.
2. Find the buffer at `rbp-0x40` and the guard at `rbp-0x9`: `0x40 - 0x9 = 55`
   bytes apart.
3. Send exactly 55 characters:
   `python3 -c "print('A'*55)" | nc <host> <port>`.

**How to protect against it:**

- Never use `scanf("%s")` without a width. Write `scanf("%54s", buf)` or use
  `fgets(buf, sizeof(buf), stdin)`.
- Remember the terminating zero byte: a string of N characters needs N + 1
  bytes. Off-by-one errors are the most common form of this bug.
- The compiler warns about an unbounded `%s` with `-Wall -Wformat`, static
  analysis finds it, and AddressSanitizer catches it at run time.
