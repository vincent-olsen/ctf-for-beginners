flag = "flag{l3ts_u5e_4_key_n3xt_t1me}"
print(f"Flag: {flag}")

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
print(f"Encrypted flag: {encrypted_flag}")

with open("../distfiles/flag.enc", "w", encoding="utf-8") as file:
    file.write(encrypted_flag)
