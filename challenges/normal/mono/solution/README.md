Each letter in the alphabet, both lowercase and uppercase, needs to be replaced
with the correct letters.

This usually requires a lot of trial and error. It can also be cheesed with an
online tool.

We can use `tr` (translate) when we have figured out the key.

```bash
cat mono_enc.txt | tr 'pitlrdhfczegoxyavujqkbmnswPITLRDHFCZEGOXYAVUJQKBMNSW' 'a-zA-Z'
```

```
Monoalphabetic substitution codes, also recognized as basic replacement codes,
represent a form of encoding technique whereby every character in the original
message is swapped with a predetermined corresponding character in the encoded
message. To illustrate, in a straightforward Caesar code, each character
is shifted by a fixed amount within the alphabet. Despite their historical
use for securing communications, monoalphabetic substitution codes are now
widely seen as insecure in contemporary cryptographic contexts, primarily
due to various notable vulnerabilities.

A primary issue undermining the security of monoalphabetic substitution codes
is their dearth of entropy. Entropy denotes the level of randomness or
unpredictability present in an encoded message. In monoalphabetic substitution
codes, the link between the original message and the encoded one is one-
to-one, meaning each character in the original message corresponds to the
same character in the encoded message. This predictable pattern exposes the
code to frequency analysis assaults, wherein an adversary can scrutinize
the frequency distribution of characters in the encoded message and infer
probable substitutions for the original characters. For instance, in English
, the letter "e" is the most frequently used, allowing an adversary to deduce
that the most prevalent character in the encoded message likely represents
"e" in the original text. Such susceptibility severely compromises the code's
security, facilitating the deciphering of the entire message through frequency
-based exploits.

Another vulnerability of monoalphabetic substitution codes is their
susceptibility to known-plaintext attacks. In these attacks, an adversary
possesses both the original message and its corresponding encoded version.
Since each character in the original message maps to the same character in the
encoded one, an adversary can effortlessly discern the substitution pattern
and construct a reverse mapping from the encoded message to the original
text. Once the substitution pattern is deciphered, the entirety of the encoded
message becomes readable, nullifying the code's efficacy in preserving message
confidentiality.

Furthermore, monoalphabetic substitution codes offer no defense against pattern
analysis assaults. In pattern analysis attacks, an adversary seeks recurring
patterns or sequences of characters in the encoded message to glean insights
into the original text. Given that each character in the original message
corresponds to the same character in the encoded one, the patterns and
structures of the original message persist in the encoded version, rendering
it susceptible to pattern analysis attacks. For example, common words, phrases,
or letter combinations in the original message would manifest as identical
patterns in the encoded message, furnishing adversaries with clues about
the underlying communication.

In summary, the insecurity of monoalphabetic substitution codes stems from
their lack of entropy, susceptibility to frequency analysis attacks,
vulnerability to known-plaintext attacks, and weakness against pattern analysis
assaults. These vulnerabilities render monoalphabetic substitution codes
inadequate for ensuring robust confidentiality and integrity in contemporary
cryptographic contexts. Consequently, more advanced encryption techniques
, such as polyalphabetic substitution codes, symmetric key algorithms, and
public key cryptography, have been devised and widely embraced to facilitate
secure communication.

The flag is: flag{y_waste_time_say_lot_word_when_few_word_do_trick}
```

## Debrief: what you learn and how to protect against it

**What you learn:** monoalphabetic substitution, and frequency analysis as the way
to break it. The key space is huge (26! possible alphabets), yet the cipher falls
in minutes, because the language's statistics survive: the most common symbol is
probably `e`, a single-letter word is `a` or `I`, and so on. A big key space alone
does not make a cipher secure.

**The solve in short:**

1. Count how often each letter appears and compare with English letter
   frequencies, or paste the text into an online solver (quipqiup, dCode).
2. Fill in short, common words (`the`, `and`, `a`) and correct as the text
   becomes readable.
3. Apply the finished key, e.g. with `tr`, and read the flag in the last line.

**How to protect against it:**

- The decrypted text explains it itself: a one-to-one mapping leaks frequencies
  and patterns. Modern ciphers produce output that looks random, where the same
  plaintext letter never maps to the same output twice.
- Use AES-GCM or ChaCha20-Poly1305 from a standard library instead of anything
  hand-made.
