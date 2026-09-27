import pytest
from parser.security import populate_security
from domain.models import ProxyConfig
from parser.exceptions import ValidationError

def get_base_config():
    return ProxyConfig(raw_url="", protocol="vless", server="1.1.1.1", port=443)

def test_security_tls_full():
    c = get_base_config()
    q = {"security": "tls", "sni": "ex.com", "alpn": "h2,http/1.1", "fp": "chrome", "ech": "1", "pcs": "a", "vcn": "b"}
    consumed = populate_security(c, q, c.server)
    assert c.security_type == "tls"
    assert c.tls.server_name == "ex.com"
    assert c.tls.alpn == ["h2", "http/1.1"]
    assert c.tls.fingerprint == "chrome"
    assert c.tls.ech_config_list == "1"
    assert c.tls.pinned_peer_cert_sha256 == "a"
    assert c.tls.verify_peer_cert_by_name == "b"

def test_security_tls_fallback():
    c = get_base_config()
    q = {"security": "tls"}
    populate_security(c, q, c.server)
    assert c.security_type == "tls"
    assert c.tls.server_name == "1.1.1.1"

def test_security_reality_valid():
    c = get_base_config()
    q = {"security": "reality", "sni": "ex.com", "pbk": "123456", "fp": "firefox", "sid": "abc", "spx": "/", "pqv": "1"}
    populate_security(c, q, c.server)
    assert c.security_type == "reality"
    assert c.reality.public_key == "123456"
    assert c.reality.short_id == "abc"
    assert c.reality.spider_x == "/"
    assert c.reality.mldsa65_verify == "1"

def test_security_reality_missing_pbk():
    c = get_base_config()
    with pytest.raises(ValidationError, match="requires pbk"):
        populate_security(c, {"security": "reality", "sni": "ex.com", "fp": "test"}, c.server)

def test_security_reality_missing_fp():
    c = get_base_config()
    consumed = populate_security(c, {"security": "reality", "pbk": "key"}, "1.2.3.4")
    assert "fp" not in consumed
    assert c.tls.fingerprint == "chrome"
def test_security_none():
    c = get_base_config()
    populate_security(c, {"security": "none"}, c.server)
    assert c.security_type == "none"

def test_security_default_fallback():
    c = get_base_config()
    populate_security(c, {}, c.server)
    assert c.security_type == "none"

def test_security_invalid_case():
    c = get_base_config()
    with pytest.raises(ValidationError):
        populate_security(c, {"security": "TLS"}, c.server)

def test_security_empty_sni():
    c = get_base_config()
    with pytest.raises(ValidationError, match="empty SNI"):
        populate_security(c, {"security": "tls", "sni": ""}, c.server)

def test_security_empty_fp():
    c = get_base_config()
    with pytest.raises(ValidationError, match="empty fp"):
        populate_security(c, {"security": "tls", "fp": ""}, c.server)

def test_security_empty_sec():
    c = get_base_config()
    with pytest.raises(ValidationError, match="empty security"):
        populate_security(c, {"security": ""}, c.server)

def test_security_allow_insecure():
    c = get_base_config()
    populate_security(c, {"security": "tls", "allowInsecure": "1"}, c.server)
    assert c.tls.allow_insecure is True
    assert any("allowInsecure" in w for w in c.parse_meta.warnings)
    
    c = get_base_config()
    populate_security(c, {"security": "tls", "allowInsecure": "0"}, c.server)
    assert c.tls.allow_insecure is False

def test_security_insecure():
    c = get_base_config()
    populate_security(c, {"security": "tls", "insecure": "true"}, c.server)
    assert c.tls.allow_insecure is True
    
    c = get_base_config()
    populate_security(c, {"security": "tls", "insecure": "false"}, c.server)
    assert c.tls.allow_insecure is False

def test_security_empty_alpn():
    c = get_base_config()
    with pytest.raises(ValidationError, match="empty ALPN"):
        populate_security(c, {"security": "tls", "alpn": ""}, c.server)

def test_security_invalid_alpn():
    c = get_base_config()
    with pytest.raises(ValidationError, match="Invalid ALPN format"):
        populate_security(c, {"security": "tls", "alpn": "h2, "}, c.server)
