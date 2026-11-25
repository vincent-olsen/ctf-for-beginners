## Setup Instructions

### Steps
1. Compile the binary (if you have the source):
   ```bash
   gcc -O0 -fno-stack-protector -no-pie -o binary binary.c
   ```

2. Test lokalt:
   ```bash
   ./binary
   ```

3. Deploy:
    - Sørg for at kun den kompilerte binæren (uten kildekode) og `flag.txt` er tilgjengelig for spilleren.
    - Hvis utfordringen hostes eksternt, kjør binæren som en tjeneste og pipe STDIN/STDOUT til en nettverkssocket.

---
