import pytest
from parser.common import decode_raw_url_base64

def test_decode_raw_url_base64_valid():
    assert decode_raw_url_base64("abc-").hex() == "69b73e"
    assert decode_raw_url_base64("abc_").hex() == "69b73f"

def test_decode_raw_url_base64_invalid():
    with pytest.raises(ValueError, match="Invalid Base64RawURL characters"):
        decode_raw_url_base64("abc\\")
    with pytest.raises(ValueError, match="Invalid Base64RawURL length"):
        decode_raw_url_base64("a")
