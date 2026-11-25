
# Setup

### Compile + Strip CET (Control-Flow Enforcement)

```bash
# Compile the vulnerable binary with all protections disabled
gcc binary.c -o binary.tmp -fcf-protection=none -fno-stack-protector -no-pie -z execstack
```

* `-fcf-protection=none`: Disables Control-Flow Enforcement Technology (CET), including shadow stack (SHSTK) and indirect branch tracking (IBT), which prevent common control-flow attacks.
* `-fno-stack-protector`: Disables stack canaries, allowing buffer overflows to overwrite return addresses undetected.
* `-no-pie`: Disables Position Independent Executable (PIE), ensuring fixed memory addresses in the binary (easier exploitation).
* `-z execstack`: Makes the stack executable—useful for shellcode attacks (not required here, but common in pwn challenges).

```bash
# Strip the CET note from the binary (important for Ubuntu 22.04+)
objcopy --remove-section '.note.gnu.property' binary.tmp binary && rm binary.tmp
```

**Check that CET is removed:**
```bash
file distfiles/binary                  # Output should NOT mention IBT or SHSTK
readelf --notes ../distfiles/binary | grep -i cet || echo "no CET note"
```

### Run Locally

```bash
./binary
```




# More Buffer Overflow Challenge Info

This challenge is designed to be beginner-friendly. Here's why:

1. **Classic vulnerability**
  - Uses `gets()`, a well-known unsafe function.
  - Simple stack buffer overflow.

2. **No modern protections**
  - No stack canary
  - No PIE (addresses are static)
  - No ASLR (assumed local testing or static remote)
  - No NX
  - No CET / Shadow Stack

3. **Straightforward goal**
  - Just call the `win()` function.
  - No shellcode or complex ROP needed.

4. **No obfuscation**
  - The binary is not stripped (optional).
  - Symbols like `win` are visible.

---

### What Pre-Knowledge Is Needed

This is suitable as a **first or second** binary exploitation challenge. Players should know:

| Concept                        | Description                                                                 |
|-------------------------------|-----------------------------------------------------------------------------|
| Stack buffer overflows        | How writing past a buffer affects control flow.                             |
| Function return addresses     | How functions return and what gets overwritten during a buffer overflow.    |
| x86_64 calling conventions    | Basic stack layout (RBP, RIP, buffer, etc.).                                |
| Finding overflow offsets      | Using cyclic patterns or manual disassembly.                                |
| Basic GDB or pwntools usage   | To analyze and automate the exploit.                                        |

_Optional but helpful:_
- Reading simple assembly (e.g., `sub $0x40, %rsp`)
- Familiarity with `objdump`, `nm`, `gdb`, or plugins like `pwndbg`

---

### Summary

| Feature              | Description                             |
|----------------------|-----------------------------------------|
| **Difficulty**       | Easy                                    |
| **Exploit Type**     | Buffer Overflow                         |
| **Primary Skill**    | Control RIP via stack overflow          |
| **Protections**      | None (all disabled during compile)      |
| **Tools Used**       | pwntools / GDB                          |
| **Real-World Realism** | Low – for learning purposes            |
| **Educational Value** | High – great intro to binary exploitation |

---

**Tip:** Without the `ret` gadget, the binary might crash before reaching the flag function.
