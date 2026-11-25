/* Shared stream cipher for pwn-ai, used by both the challenge binary (to
 * decrypt at runtime) and mkenc.c (to produce flag.enc at build time), so the
 * two can never drift. The keystream is a plain xorshift64 seeded by the key, so
 * a reverser who reads win() off the disassembly can reconstruct it: the key
 * byte stream depends entirely on the 64-bit key, and XOR is its own inverse, so
 * decrypt() both encrypts and decrypts.
 *
 * The point of the challenge: the flag exists ONLY in this encrypted form (there
 * is no plaintext copy on the server), and the only key that turns it back into
 * the flag is 0xc0ffee. So the win() argument is not a gate you can jump past —
 * the right value has to be in rdi for the decryption itself to come out right. */
#ifndef PWN_AI_CIPHER_H
#define PWN_AI_CIPHER_H

#include <stddef.h>

/* XOR each byte with a xorshift64 keystream seeded by `key`. Self-inverse. */
static void decrypt(unsigned char *buf, size_t n, unsigned long key) {
    unsigned long s = key ? key : 0x9e3779b97f4a7c15UL; /* avoid a zero state */
    for (size_t i = 0; i < n; i++) {
        s ^= s << 13;
        s ^= s >> 7;
        s ^= s << 17;
        buf[i] ^= (unsigned char)s;
    }
}

#endif
