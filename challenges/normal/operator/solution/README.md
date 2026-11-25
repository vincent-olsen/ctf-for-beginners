We are given an "advanced encryption algorithm".

```py
def encrypt(message):
    encrypted_message = ""
    for char in message:
        a = (ord(char) * 2) + 12
        b = (a ^ 42) + 5
        c = (b * 3) - 7
        encrypted_char = c ^ 25
        encrypted_message += chr(encrypted_char)
    return encrypted_message
```

For each character in the flag, it scrambles it with a different character.
The scrambling is not based on a secret key, so it can be reversed.

We make a script that reads in the encrypted flag, reverses each step,
and prints out the decrypted flag:

```py
with open("flag.enc", "r") as file:
    encrypted_flag = file.read()

def decrypt(message):
    result = ""
    for char in message:
        char = ord(char) ^ 25
        char = (char + 7) // 3
        char = (char - 5) ^ 42
        char = (char - 12) // 2
        result += chr(char)
    return result

print(decrypt(encrypted_flag))
```

Let's save it as `solution.py` and run it:

```bash
$ python solution.py 
flag{l3ts_u5e_4_key_n3xt_t1me}
```

## Debrief: what you learn and how to protect against it

**What you learn:** to read code and reverse it. The "encryption" is a fixed chain
of arithmetic (`*`, `+`, `^`, `-`) with no key, so anyone who has the algorithm
can undo it by running the inverse operations in the opposite order.

**The solve in short:**

1. Read `encrypt()` and list its steps: `*2 +12`, `^42 +5`, `*3 -7`, `^25`.
2. Write `decrypt()` with each step inverted, last step first: `^25`, `+7 //3`,
   `-5 ^42`, `-12 //2`.
3. Run it on `flag.enc`.

**How to protect against it:**

- An algorithm without a key is an encoding. The security must sit in a secret
  key, not in the algorithm being unknown (Kerckhoffs's principle), because the
  code always gets out: here it is handed to the player.
- Don't write your own crypto. Use a standard library (AES-GCM,
  ChaCha20-Poly1305) and a random key that is stored apart from the data. The
  flag says the same: `l3ts_u5e_4_key_n3xt_t1me`.
