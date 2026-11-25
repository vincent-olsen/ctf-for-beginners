/* Build-time tool: read flag.txt and write flag.enc = flag encrypted under the
 * vault key 0xc0ffee, using the same cipher the challenge binary decrypts with
 * (cipher.h, shared, so they can never drift). The Makefile runs this before
 * building the binary; flag.enc is what ships in the container, and the plaintext
 * flag.txt is NOT copied into the image. */
#include <stdio.h>
#include <stdlib.h>

#include "cipher.h"

#define VAULT_KEY 0xc0ffeeUL

int main(void) {
    FILE *in = fopen("flag.txt", "rb");
    if (!in) { perror("flag.txt"); return 1; }
    unsigned char buf[128];
    size_t n = fread(buf, 1, sizeof buf, in);
    fclose(in);
    /* Strip a single trailing newline so the decrypted output is just the flag. */
    if (n && buf[n - 1] == '\n') n--;

    decrypt(buf, n, VAULT_KEY);   /* XOR cipher: same call encrypts and decrypts */

    FILE *out = fopen("flag.enc", "wb");
    if (!out) { perror("flag.enc"); return 1; }
    fwrite(buf, 1, n, out);
    fclose(out);
    return 0;
}
