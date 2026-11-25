## How to Set Up Binary2 Challenge

1. **Save the code**  
   Put the `binary.c` source file in your project folder.

2. **Create a flag file**  
   Add a `flag.txt` next to it, e.g.: `flag{buffer_overflow_basics}`

3. **Compile the binary**  
   Use CTF-friendly flags:
```bash
gcc -O0 -g -fno-stack-protector -no-pie binary.c -o binary 
```

4. **Test locally**: `./binary`
