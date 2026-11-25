#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void print_flag(void) {
    FILE *f = fopen("flag.txt", "r");
    if (!f) { puts("flag.txt missing"); exit(1); }
    char flag[128];
    if (!fgets(flag, sizeof flag, f)) { puts("read error"); exit(1); }
    printf("\n%s\n", flag);
}

static void vuln(void) {
    struct {
        char name[16];
        unsigned int guard;  /* will be overwritten if name is overflowed */
        unsigned int points;
    } u;

    u.guard  = 0x44444444;
    u.points = 10;

    setvbuf(stdout, NULL, _IONBF, 0); // unbuffered stdout for cleaner I/O in PTY
    printf("Enter your name: ");
    fgets(u.name, 64, stdin);

    printf("Hello, %s\n", u.name);
    printf("guard = 0x%08X\n", u.guard);
    printf("points = %u\n", u.points);

    if (u.guard == 0x44444444 && u.points > 9000) {
        print_flag();
    }
}

int main(void) {
    vuln();
    return 0;
}
