#include <stdio.h>
#include <string.h>

void flag_function() {
    char flag[100];
    FILE *f = fopen("flag.txt", "r");
    if (f) {
        fgets(flag, sizeof(flag), f);
        printf("\nCorrect! Here is your flag:\n%s\n", flag);
        fclose(f);
    } else {
        printf("ERROR: Flag file not found in this file! Use the container (nc address on the CTF page) to find the flag.\n");
    }
}

void i_have_something_vulnerable_here_function() {
    char buf[64];
    printf("> ");
    fgets(buf, 200, stdin);
}

int main() {
    setbuf(stdout, NULL);
    i_have_something_vulnerable_here_function();
    return 0;
}
