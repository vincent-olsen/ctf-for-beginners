with open("../distfiles/flag.enc", "r", encoding="utf-8") as file:
    encrypted_flag = file.read()

print(f"Encrypted flag: {encrypted_flag}")

def decrypt(message):
    result = ""
    for char in message:
        char = ord(char) ^ 25
        char = (char + 7) // 3
        char = (char - 5) ^ 42
        char = (char - 12) // 2
        result += chr(char)
    return result

print(f"Decrypted flag: {decrypt(encrypted_flag)}")
