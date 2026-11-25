#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "cipher.h"

/* A deliberate gadget so a clean `pop rdi ; ret` exists at a fixed address
   (the binary is no-PIE, so its address is static). You need it to control the
   first argument register before returning into win(). */
void gadget(void) { asm volatile("pop %rdi; ret"); }

/* win() takes the vault key in its first argument (rdi on x86-64) and USES it:
   the flag is stored only in encrypted form (flag.enc) and the key is the
   decryption key, not a password that is merely compared. So a plain "jump to
   win" — or returning past the key check to the print — is not enough: without
   0xc0ffee in rdi the decryption comes out as garbage, because there is no
   plaintext copy of the flag anywhere on the server. */
void win(unsigned long key) {
    FILE *f = fopen("flag.enc", "r");
    if (!f) { puts("flag.enc missing on the server"); return; }
    unsigned char buf[128];
    size_t n = fread(buf, 1, sizeof buf, f);
    fclose(f);

    /* Decrypt with whatever key we were handed. Only 0xc0ffee yields the flag;
       any other value fills buf with noise. */
    decrypt(buf, n, key);

    if (key == 0xc0ffeeUL) {
        puts("[+] correct key — the vault opens:");
        fwrite(buf, 1, n, stdout);
    } else {
        puts("[-] wrong key — that key decrypts to nothing but static.");
    }
}

void vuln(void) {
    char buf[64];
    puts("Speak, friend, and enter.");
    read(0, buf, 256);            /* BUG: 256 bytes into a 64-byte buffer */
    printf("You said: %s\n", buf);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
    vuln();
    return 0;
}
