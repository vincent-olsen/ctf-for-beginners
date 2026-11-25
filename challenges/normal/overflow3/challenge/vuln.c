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
        unsigned int guard;
        unsigned int points;
    } u;

    u.guard  = 0x44414544;
    u.points = 10;

    setvbuf(stdout, NULL, _IONBF, 0);

    printf("Enter your name: ");
    fgets(u.name, 128, stdin);

    printf("Hello, %s\n", u.name);
    printf("guard = 0x%08X\n", u.guard);
    printf("points = %u\n", u.points);

    if (u.guard == 0x44414544 && u.points == 2680) {
        print_flag();
    }
}

int main(void) {
    vuln();
    return 0;
}
