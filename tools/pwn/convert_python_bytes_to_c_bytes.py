python_bytes = [88, 150, 249, 3, 125, 220, 221, 162, 155, 252, 42, 84, 21, 73, 158, 228, 234, 219, 205, 144, 204, 166, 63, 10]
c_byte_array = ', '.join(f'0x{b:X}' for b in python_bytes)
print(f'unsigned char encrypted_flag[] = {{{c_byte_array}}};')

