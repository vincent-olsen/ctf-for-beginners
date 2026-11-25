#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void hidden_function() {
    /* Scratch exploit-dev file (not a packaged challenge); flag redacted. */
    unsigned char flag[] = "flag{REDACTED_SCRATCH}";

    char key[] = "you_got_pwnd";
    srand(12345);
    FILE *fp; 

    for (int i = 0; i < sizeof(flag); i++) {
        flag[i] ^= (rand() % 256) ^ key[i % strlen(key)];
    }

    printf("Decoded flag: %s\n", flag);

    
    fp = fopen("output.txt", "w");
    if (fp != NULL) {
        fprintf(fp, "%s\n", flag);
        fclose(fp); 
    } else {
        printf("Failed to write to file\n");
    }
}

int main() {
    char input[64];
    printf("Enter password: ");
    fgets(input, sizeof(input), stdin);
    input[strcspn(input, "\n")] = 0; 

    if (strcmp(input, "you_got_pwnd") == 0) {
        printf("Access Granted.\n");
        hidden_function();
    } else {
        printf("Access Denied.\n");
    }
    return 0;
}

