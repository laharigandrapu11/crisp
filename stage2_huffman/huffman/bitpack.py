def bits_to_bytes(bits: str) -> bytes:
    pad_length = (8 - (3 + len(bits)) % 8) % 8
    full = format(pad_length, "03b") + bits + "0" * pad_length
    result = bytearray()
    for i in range(0, len(full), 8):
        result.append(int(full[i:i + 8], 2))
    return bytes(result)


def bytes_to_bits(data: bytes) -> str:
    if not data:
        return ""
    full = "".join(format(byte, "08b") for byte in data)
    pad_length = int(full[:3], 2)
    if pad_length > 0:
        return full[3:-pad_length]
    return full[3:]
