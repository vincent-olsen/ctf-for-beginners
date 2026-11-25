## How to Create This Challenge

1. **Write the code**  
   Use a packed struct with a buffer and a guard byte, e.g. `char buf[14]; unsigned char guard;`.

2. **Compile**
   ```bash
   gcc -O0 -g -fno-stack-protector -no-pie addr_math_intro.c -o binary

3. **Add a flag**
Create flag.txt with your flag inside, e.g.: `flag{addr_math_basics}`

4. **Run locally** `./binary`

