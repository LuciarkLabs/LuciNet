import base64


def decode_base64(b64_string: str) -> str:
    """رفع مشکل پدینگ در Base64 و دیکد کردن آن"""
    b64_string = b64_string.strip()
    b64_string += "=" * ((4 - len(b64_string) % 4) % 4)
    return base64.b64decode(b64_string).decode("utf-8")
