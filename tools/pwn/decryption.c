#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void decrypt_flag() {
    unsigned char encrypted_flag[] =  {0x58, 0x96, 0xF9, 0x3, 0x7D, 0xDC, 0xDD, 0xA2, 0x9B, 0xFC, 0x2A, 0x54, 0x15, 0x49, 0x9E, 0xE4, 0xEA, 0xDB, 0xCD, 0x90, 0xCC, 0xA6, 0x3F, 0xA;
 
    char key[] = "you_got_pwnd";
    int flag_len = sizeof(encrypted_flag);
    int key_len = strlen(key);

    srand(12345); // Ensure the same seed for the pseudo-random number generator

    for (int i = 0; i < flag_len; i++) {
        // Reverse the encryption: Apply XOR again with the same random sequence and key
        encrypted_flag[i] ^= (rand() % 256) ^ key[i % key_len];
    }

    printf("Decrypted flag: %s\n", encrypted_flag);
}

int main() {
    printf("Decrypting the flag...\n");
    decrypt_flag();
    return 0;
}

