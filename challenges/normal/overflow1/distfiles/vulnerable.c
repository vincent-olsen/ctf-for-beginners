#include <stdio.h>
#include <stdlib.h>

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
        int  points;
    } u;

    u.points = 10;

    printf("Enter your name: ");

    // BUG: second argument to fgets MUST be the destination buffer size.
    // Passing 32 here overflows u.name (16 bytes) if input >16 chars.
    fgets(u.name, 32, stdin);

    printf("Hello, %s\n", u.name);
    printf("You have %i points\n", u.points);

    if (u.points > 9000) {
        print_flag();
    }
}

int main(void) {
    vuln();
    return 0;
}
