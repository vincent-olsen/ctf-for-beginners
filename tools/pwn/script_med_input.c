#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void hidden_function() {
    // Use a macro to define the flag at compile-time
    unsigned char flag[] = FLAG; // Use the macro here
    char key[] = "you_got_pwnd";
    srand(12345); // Fixed seed for repeatability
    FILE *fp; // File pointer

    int flag_len = sizeof(flag) - 1; // Adjust for null terminator in the array size calculation

    for (int i = 0; i < flag_len; i++) {
        flag[i] ^= (rand() % 256) ^ key[i % strlen(key)];
    }

    printf("Decoded flag: %s\n", flag);

    // Open file output.txt for writing
    fp = fopen("output.txt", "w");
    if (fp != NULL) {
        fprintf(fp, "%s\n", flag);
        fclose(fp); // Close the file
    } else {
        printf("Failed to write to file\n");
    }
}

int main() {
    char input[64];
    printf("Enter password: ");
    fgets(input, sizeof(input), stdin);
    input[strcspn(input, "\n")] = 0; // Remove the newline

    if (strcmp(input, "you_got_pwnd") == 0) {
        printf("Access Granted.\n");
        hidden_function();
    } else {
        printf("Access Denied.\n");
    }
    return 0;
}

