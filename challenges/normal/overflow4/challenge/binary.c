#include <stdio.h>

__attribute__((noinline))
void flag_function(void) {
    char flag[128] = {0};
    FILE *f = fopen("flag.txt", "r");
    if (f) {
        fgets(flag, sizeof(flag), f);
        printf("\nCorrect! Here is your flag:\n%s\n", flag);
        fclose(f);
    } else {
        printf("ERROR: Flag file not found in this file! Use the container (nc address on the CTF page) to find the flag.\n");
    }
}

__attribute__((noinline))
void theres_is_a_specific_byte_size_to_hit_here_function(void) {
    struct __attribute__((packed)) {
            char buf[55];
            volatile unsigned char key;
    } frame = { .key = 0xFF };

    printf("Enter the right amount of characters here: ");
    scanf("%s", frame.buf);

    if (frame.key == 0x00) {
        puts("\nNice! You found the required amount of bytes and overflowed the guard.");
        flag_function();
    } else {
        puts("You didn't hit the right byte size! Try again.");
    }
}

int main(void) {
    setbuf(stdout, NULL);
    theres_is_a_specific_byte_size_to_hit_here_function();
    return 0;
}
