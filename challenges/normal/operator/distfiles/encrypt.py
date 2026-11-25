flag = "flag{REDACTED}"

def encrypt(message):
    encrypted_message = ""
    for char in message:
        a = (ord(char) * 2) + 12
        b = (a ^ 42) + 5
        c = (b * 3) - 7
        encrypted_char = c ^ 25
        encrypted_message += chr(encrypted_char)
    return encrypted_message

encrypted_flag = encrypt(flag)

with open("flag.enc", "w", encoding="utf-8") as file:
    file.write(encrypted_flag)
