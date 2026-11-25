// binary2.c
#include <stdio.h>
#include <string.h>
#include <stddef.h>  // offsetof

__attribute__((noinline))
void flag_function(void) {
    char flag[128] = {0};
    FILE *f = fopen("flag.txt", "r");
    if (f) {
        if (fgets(flag, sizeof(flag), f)) {
            // Strip trailing newline if present
            flag[strcspn(flag, "\r\n")] = '\0';
            printf("\nCorrect! Here is your flag:\n%s\n", flag);
        } else {
            printf("ERROR: Failed reading flag.txt.\n");
        }
        fclose(f);
    } else {
        printf("ERROR: Flag file not found in this file! Use the container (nc address on the CTF page) to find the flag.\n");
    }
}

// Return 1 if flag loaded, 0 otherwise (prints error on failure)
static int load_flag_prefix(char *out, size_t cap, size_t *out_len) {
    if (!out || cap == 0 || !out_len) return 0;
    out[0] = '\0';
    *out_len = 0;

    FILE *f = fopen("flag.txt", "r");
    if (!f) {
        printf("ERROR: Flag file not found in this file! Use the container (nc address on the CTF page) to find the flag.\n");
        return 0;
    }

    if (!fgets(out, cap, f)) {
        printf("ERROR: Failed reading flag.txt.\n");
        fclose(f);
        return 0;
    }
    fclose(f);

    out[strcspn(out, "\r\n")] = '\0';
    *out_len = strlen(out);
    return 1;
}

__attribute__((noinline))
void bof_challenge(void) {
    struct __attribute__((packed)) Frame {
        char buf[24];
        volatile unsigned char key;
    } frame = { .key = 0xFF };

    // Pre-read the flag so we can leak a prefix when appropriate.
    char flag[128] = {0};
    size_t flag_len = 0;
    int have_flag = load_flag_prefix(flag, sizeof(flag), &flag_len);

    const size_t distance = offsetof(struct Frame, key); // 24 with 'packed'

    char tmp[256];

    printf("Enter your input: ");
    if (!fgets(tmp, sizeof(tmp), stdin)) {
        puts("Input error / EOF.");
        return;
    }

    // Strip trailing newline if present
    tmp[strcspn(tmp, "\n")] = '\0';

    size_t len = strlen(tmp);
    printf("You entered: %zu bytes\n", len);

    if (len < 5) {
        puts("Too few characters... nothing happens!");
        return;
    }

    if (len > distance) { // overshoot
        puts("Too many characters! You overshot the target — no flag for overshoots. Have you tried looking at the objdump of the binary?");
        return;
    }

    // Tease progress without disclosing the answer: show only the fixed "flag{"
    // opening, never more, regardless of input length. (This used to leak `len`
    // real characters, so a 23-byte input revealed all but the closing brace.)
    if (have_flag && flag_len > 0) {
        const size_t teaser = 5; // "flag{"
        size_t leak_len = flag_len < teaser ? flag_len : teaser;
        printf("Leaked: %.*s...\n", (int)leak_len, flag);
    }

    // Perform the intentional overflow only when len <= distance.
    // - len < 24: entirely inside buf → key stays 0xFF
    // - len == 24: NUL lands on key → key becomes 0x00 (success)
    strcpy(frame.buf, tmp); // vulnerability on purpose

    if (len == distance) {
        if (frame.key == 0x00) {
            puts("\nNice! You found the required amount of bytes and overflowed the guard.");
            flag_function();
        } else {
            // Extremely unlikely with fgets/strcpy; keep a helpful note.
            puts("Length looked right but guard wasn't zero — avoid embedded NULs/non-ASCII.");
        }
    } else { // 5..23
        puts("Keep going...");
    }
}

int main(void) {
    setbuf(stdout, NULL);
    bof_challenge();
    return 0;
}
