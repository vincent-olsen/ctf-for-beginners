We are given a string that is "encrypted".

```
iodj{wkh_hpsluh_ihoo_iru_d_uhdvrq}
```

We can see that the curlybraces and underscores are unchanged.
The string starts with four letters as well, just as our flag.
Looks like the characters are just replaced.

We could manually try to decrypt this.
By looking at the proximity of characters, it looks like
they are shifted a number of characters up.

The `i` becomes `f` if shifted 3 down.
The `o` becomes `l` if shifted 3 down.
The `d` becomes `a` if shifted 3 down.
And so on..

This is known as a Caesar Cipher.

We can use a website called `cyberchef` to decrypt this.
All we need to do is plug the string into the `input` of
the website, and with a simple cipher such as this, it should
automatically find the answer.
If not, we can find the `rot13` (rotate 13) operation and
configure it to rotate 3 characters down.

```
flag{the_empire_fell_for_a_reason}
```

## Debrief: what you learn and how to protect against it

**What you learn:** the Caesar cipher: every letter is shifted the same number of
places. There are only 25 possible keys, so it is broken by trying all of them.
The known start of the message (`flag{`) gives the key away immediately, which is
a first taste of a known-plaintext attack.

**The solve in short:**

1. Notice that `{`, `}` and `_` are untouched and that the text starts with four
   letters: `iodj` must be `flag`.
2. `i` to `f` is three steps back, and so are the others: the shift is 3.
3. Shift everything back by 3 (CyberChef ROT13 with amount 23 or -3, or simply
   try all 25).

**How to protect against it:**

- A cipher is only as strong as its number of possible keys, and 25 is nothing.
  Use modern, reviewed ciphers (AES-256-GCM, ChaCha20-Poly1305) from a standard
  library, and never design your own.
- Assume the attacker knows part of the plaintext (file headers, greetings, a
  flag format). A good cipher stays secure anyway.
