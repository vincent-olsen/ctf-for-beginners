
# If reading from a file:
with open('output.txt', 'rb') as file:
    encrypted_bytes = file.read()

# Convert to byte array
byte_array = list(encrypted_bytes)
print(byte_array)

