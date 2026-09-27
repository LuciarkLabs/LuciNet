import pytest
from parser.common import strict_unquote, safe_urlparse, get_host_port, parse_finalmask, process_unknown_params, set_lossless, parse_xray_uuid
from parser.exceptions import ParseError, ValidationError
from domain.models import ProxyConfig

def test_strict_unquote_valid():
    assert strict_unquote("abc%20def") == "abc def"
    assert strict_unquote("abc%2F") == "abc/"
    assert strict_unquote("%0A") == "\n"
    assert strict_unquote("a%00b") == "a\x00b"
    assert strict_unquote("a%FFb") == "a\ufffdb"
    assert strict_unquote("%E4%BD%A0%E5%A5%BD") == "你好"
    assert strict_unquote("%25") == "%"

def test_strict_unquote_invalid():
    with pytest.raises(ParseError): strict_unquote("abc%ZZ")
    with pytest.raises(ParseError): strict_unquote("abc%2")

def test_safe_urlparse():
    parsed = safe_urlparse("vless://user@1.2.3.4:443")
    assert parsed.scheme == "vless"

def test_safe_urlparse_invalid():
    with pytest.raises(ParseError):
        safe_urlparse("vless://[::1/path")

def test_get_host_port_valid():
    parsed = safe_urlparse("vless://user@1.2.3.4:443")
    host, port = get_host_port(parsed)
    assert host == "1.2.3.4"
    assert port == 443

def test_get_host_port_invalid():
    parsed = safe_urlparse("vless://user@1.2.3.4:65536ab")
    with pytest.raises(ValidationError):
        get_host_port(parsed)

def test_get_host_port_empty_hostname():
    parsed = safe_urlparse("vless://user@:443")
    h, p = get_host_port(parsed)
    assert h == ""

def test_uuid_go_simulation_invalid():
    with pytest.raises(ValueError, match="Invalid UUID hex"):
        parse_xray_uuid("123456781234123412341234567890ZZ")
    with pytest.raises(ValueError, match="extra characters"):
        parse_xray_uuid("12345678123412341234123456789012a")

def test_parse_finalmask():
    c = ProxyConfig(raw_url="", protocol="v", server="1", port=1)
    parse_finalmask("", c)
    assert c.finalmask_raw == ''
    
    parse_finalmask('{"a":1}', c)
    assert c.finalmask == {"a": 1}
    
    parse_finalmask("not_json", c)
    assert c.finalmask is None
    assert "FinalMask is not a valid JSON dict" in c.parse_meta.warnings
    assert c.parse_meta.lossless is False

    c2 = ProxyConfig(raw_url="", protocol="v", server="1", port=1)
    parse_finalmask('"string_not_dict"', c2)
    assert c2.finalmask is None
    assert c2.parse_meta.lossless is False

def test_process_unknown_params():
    c = ProxyConfig(raw_url="", protocol="v", server="1", port=1)
    c.parse_meta.lossless = None
    process_unknown_params({"a": 1, "b": 2}, {"a"}, c)
    assert c.parse_meta.unknown_params == {"b": "2"}
    assert c.parse_meta.lossless is False

    c2 = ProxyConfig(raw_url="", protocol="v", server="1", port=1)
    c2.parse_meta.lossless = None
    process_unknown_params({"a": 1}, {"a"}, c2)
    assert c2.parse_meta.lossless is True

def test_set_lossless():
    c = ProxyConfig(raw_url="", protocol="v", server="1", port=1)
    c.parse_meta.lossless = False
    set_lossless(c, True)
    assert c.parse_meta.lossless is False
