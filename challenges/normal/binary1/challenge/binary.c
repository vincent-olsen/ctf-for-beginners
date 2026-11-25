// addr_math_intro.c
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <stdlib.h>
#include <errno.h>

__attribute__((noinline))
void print_flag(void) {
    char flag[256] = {0};
    FILE *f = fopen("flag.txt", "r");
    if (!f) {
        puts("ERROR: Flag file not found in this file! Use the container (nc address on the CTF page) to find the flag.\n");
        return;
    }
    fgets(flag, sizeof(flag), f);
    fclose(f);
    // trim newline
    flag[strcspn(flag, "\r\n")] = '\0';
    printf("\nCorrect! Here is your flag:\n%s\n", flag);
}

int main(void) {
    setbuf(stdout, NULL);

    // A tiny packed frame so the addresses are adjacent with a known spacing.
    struct __attribute__((packed)) Frame {
        char buf[14];                 // start address we show
        volatile unsigned char guard; // target address we show
    } frame;

    // Compute the true distance in bytes (what we want the player to calculate)
    size_t distance = (size_t)((unsigned char*)&frame.guard
                             - (unsigned char*)frame.buf);

    printf("For reference:\n");
    printf("  the buffer starts at:        %p  (\"A\")\n", (void*)frame.buf);
    printf("  the target guard byte at:    %p  (\"B\")\n", (void*)&frame.guard);
    printf("\nHow to solve:\n");
    printf("  1) Subtract the addresses as numbers:  B - A  =  0x??\n");
    printf("  2) Convert that hex result to decimal bytes.\n");
    printf("  3) Enter your answer (decimal like 24, or hex like 0x18).\n\n");

    printf("Your answer (bytes): ");

    char line[128];
    if (!fgets(line, sizeof(line), stdin)) {
        puts("Input error / EOF.");
        return 1;
    }

    errno = 0;
    char *end = NULL;
    unsigned long long guess = strtoull(line, &end, 0);
    if (errno != 0 || end == line) {
        puts("Couldn't parse a number.");
        return 1;
    }

    printf("You entered: %llu bytes\n", guess);

    if (guess == distance) {
        print_flag();
    } else {
        if (guess < distance) puts("\nToo low.");
        else                  puts("\nToo high.");
        printf("Tip: Re-check the hex subtraction (B - A) and convert to decimal bytes.\n");
    }

    return 0;
}
