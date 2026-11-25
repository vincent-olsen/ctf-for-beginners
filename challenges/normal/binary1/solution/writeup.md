## Challenge: Address Math Intro

The program prints two memory addresses:

* buffer starts at: 0x7ffec6b8f4b0 ("A")
* guard byte at: 0x7ffec6b8f4be ("B")

### Task
1. Subtract them: `B - A = 0x0e`
2. Convert hex to decimal: `0x0e = 14`
3. Enter `14` (or `0x0e`) to get the flag.

### How to Solve
1. **Think of addresses as numbers.**  
   Every memory address points to a byte in RAM. So `0x7ffec6b8f4b0` is just a number written in hexadecimal.

2. **Subtract the start from the guard:**  `B - A = 0x7ffec6b8f4be - 0x7ffec6b8f4b0 = 0x0e`

3. **Convert hex to decimal:** `0x0e = 14`

4. **Interpret the result:**  
   The guard byte is **14 bytes after** the start of the buffer.  
   That means if you were filling the buffer with input, it would take 14 characters (since 1 char = 1 byte) to reach the guard.

5. **Enter the number:**  
   Input `14` (or `0x0e`) when asked, and the program will unlock the flag.

### Takeaway
- Memory addresses are numeric.
- The difference between two addresses = distance in **bytes**.
- In this challenge, the buffer is 14 bytes long, so the guard byte sits exactly 14 bytes away.

## Debrief: what you learn and how to protect against it

**What you learn:** memory addresses are just numbers, usually written in
hexadecimal. The distance between two addresses is the number of bytes between
them, which is the calculation every buffer overflow starts with. (Retired for
the current event: the `overflow` series covers it.)

**The solve in short:**

1. The program prints the address of the buffer and of the guard byte.
2. Subtract them: `0x...be - 0x...b0 = 0x0e`.
3. Convert to decimal (14) and enter it.

**How to protect against it:** there is no bug to exploit here, it is a warm-up.
The real-world point is the address leak.

- Modern systems place the stack, heap and libraries at random addresses (ASLR),
  and an exploit usually needs to know where things are. A program that prints
  pointers gives that away.
- Don't print or log raw addresses (`%p`) in production, and don't show them in
  error messages.
