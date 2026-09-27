import pytest
from parser.common import parse_xray_uuid

def test_parse_xray_uuid_valid():
    assert parse_xray_uuid("example") == "feb54431-301b-52bb-a6dd-e1e93e81bb9e"
    assert parse_xray_uuid("-12345678123412341234123456789012") == "12345678-1234-1234-1234-123456789012"

def test_parse_xray_uuid_invalid():
    with pytest.raises(ValueError, match="too short"):
        parse_xray_uuid("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
