import pytest

def test_semantic_invariants_connection_hash_invariance(parser_factory):
    
    url1 = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=tcp&security=none"
    url2 = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=ws&security=tls&sni=ex.com"
    url3 = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=grpc&security=reality&pbk=123&fp=chrome"
    
    c1 = parser_factory.parse_url(url1)
    c2 = parser_factory.parse_url(url2)
    c3 = parser_factory.parse_url(url3)
    
    assert c1.connection_hash == c2.connection_hash == c3.connection_hash
    
    assert c1.config_hash != c2.config_hash
    assert c2.config_hash != c3.config_hash

def test_semantic_invariants_connection_hash_sensitivity(parser_factory):
    base_url = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=tcp&security=none"
    base_config = parser_factory.parse_url(base_url)
    
    diff_server = parser_factory.parse_url("vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@5.6.7.8:443?type=tcp&security=none")
    assert base_config.connection_hash != diff_server.connection_hash
    
    diff_port = parser_factory.parse_url("vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:444?type=tcp&security=none")
    assert base_config.connection_hash != diff_port.connection_hash
    
    diff_auth = parser_factory.parse_url("vless://aaaaa431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=tcp&security=none")
    assert base_config.connection_hash != diff_auth.connection_hash

def test_semantic_invariants_shadowsocks_formats(parser_factory):
    
    url_sip = "ss://YWVzLTEyOC1nY206cGFzcw==@1.2.3.4:443#rem"
    
    url_legacy = "ss://YWVzLTEyOC1nY206cGFzc0AxLjIuMy40OjQ0Mw==#rem"
    
    url_raw = "ss://aes-128-gcm:pass@1.2.3.4:443#rem"
    
    c_sip = parser_factory.parse_url(url_sip)
    c_legacy = parser_factory.parse_url(url_legacy)
    c_raw = parser_factory.parse_url(url_raw)
    
    assert c_sip.connection_hash == c_legacy.connection_hash == c_raw.connection_hash
    assert c_sip.config_hash == c_legacy.config_hash == c_raw.config_hash
    
    assert c_sip.parse_meta.source_format == "shadowsocks_base64_userinfo"
    assert c_legacy.parse_meta.source_format == "shadowsocks_legacy_base64"
    assert c_raw.parse_meta.source_format == "shadowsocks_sip002"
