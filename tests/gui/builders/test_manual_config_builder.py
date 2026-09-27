import pytest
from gui.builders.manual_config_builder import ManualConfigBuilder, ManualConfigInput
from parser.factory import ParserFactory
from parser.exceptions import ValidationError, ParseError

@pytest.fixture
def parser_factory():
    return ParserFactory()

def assert_parses(url, factory):
    """Parses and returns ProxyConfig"""
    return factory.parse_url(url)

def test_vless_raw_none(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="raw", security="none")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "vless"
    assert p.server == "1.1.1.1"
    assert p.transport.network == "raw"
    assert p.security_type == "none"

def test_vless_ws_tls(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="ws", security="tls", path="/chat", host="ex.com", sni="ex.com", fp="chrome")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.transport.network == "websocket"
    assert p.transport.path == "/chat"
    assert p.transport.host == "ex.com"
    assert p.tls.server_name == "ex.com"

def test_vless_grpc_tls(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="grpc", security="tls", service_name="myservice", grpc_mode="multi")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.transport.network == "grpc"
    assert p.transport.grpc_service_name == "myservice"
    assert p.transport.grpc_mode == "multi"

def test_vless_xhttp(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="xhttp", security="none", path="/", xhttp_mode="auto", xhttp_extra="abc")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.transport.network == "xhttp"
    assert p.transport.path == "/"

def test_vless_mkcp(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="mkcp", security="none", mkcp_mtu="1350")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.transport.network == "mkcp"

def test_vless_httpupgrade(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="httpupgrade", security="none", path="/upgrade")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.transport.network == "httpupgrade"
    assert p.transport.path == "/upgrade"

def test_vless_reality_raw(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="raw", security="reality", pbk="123", sid="456", spx="/", pqv="0")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.security_type == "reality"
    assert p.reality.public_key == "123"

def test_vless_invalid_reality(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="ws", security="reality", pbk="123")
    import pytest
    with pytest.raises(ValueError, match="Reality is not supported with network"):
        ManualConfigBuilder.build(inp)

def test_vless_flows(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="raw", security="tls", flow="xtls-rprx-vision")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.flow == "xtls-rprx-vision"

def test_vless_mlkem(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="a-b-c-d", network="raw", security="none", encryption="mlkem768x25519plus.native.1rtt.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.encryption.startswith("mlkem768")

def test_vmess_aead(parser_factory):
    inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", network="ws", security="tls", path="/")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "vmess"
    assert p.transport.network == "websocket"
    assert p.security_type == "tls"

def test_vmess_legacy(parser_factory):
    inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", network="ws", security="tls", path="/", vmess_mode="legacy")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "vmess"
    assert p.transport.network == "websocket"
    assert p.security_type == "tls"

def test_trojan(parser_factory):
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="pass", network="ws", security="tls", path="/")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "trojan"
    assert p.password == "pass"
    assert p.transport.network == "websocket"

def test_ss_sip002(parser_factory):
    inp = ManualConfigInput(protocol="ss", server="1.1.1.1", port=443, auth="pass", ss_method="aes-128-gcm", ss_uot=True, ss_plugin="obfs-local")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "shadowsocks"
    assert p.method == "aes-128-gcm"
    assert p.password == "pass"
    assert p.ss_uot is True
    assert p.parse_meta.extensions["ss_plugin"] == "obfs-local"

def test_ipv6(parser_factory):
    inp = ManualConfigInput(protocol="ss", server="2001:db8::1", port=443, auth="pass", ss_method="aes-128-gcm")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.server == "2001:db8::1"


def test_vless_hysteria(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network="hysteria", security="tls")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.transport.network == "hysteria"

def test_vless_hysteria_non_tls(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network="hysteria", security="none")
    import pytest
    with pytest.raises(ValueError, match="Hysteria requires TLS security"):
        ManualConfigBuilder.build(inp)
def test_vless_invalid_mlkem(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network="raw", security="none", encryption="invalid.encryption")
    url = ManualConfigBuilder.build(inp)
    with pytest.raises(ValidationError, match="missing blocks"):
        assert_parses(url, parser_factory)

def test_vmess_aead_grpc(parser_factory):
    inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", network="grpc", security="tls", grpc_mode="multi")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "vmess"
    assert p.transport.network == "grpc"

def test_trojan_xhttp(parser_factory):
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="pass", network="xhttp", security="tls", xhttp_mode="auto", xhttp_extra="abc")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.transport.network == "xhttp"

def test_ss_ipv4(parser_factory):
    inp = ManualConfigInput(protocol="ss", server="1.2.3.4", port=443, auth="pass", ss_method="aes-128-gcm")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.server == "1.2.3.4"

def test_special_chars_remark(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", remark="My Special # Remark ? &")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.remark == "My Special # Remark ? &"

def test_special_chars_path(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network="ws", security="none", path="/my path?abc=1")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.transport.path == "/my path?abc=1"

def test_final_mask(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", final_mask='{"a":1}')
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.finalmask == {"a": 1}


def test_vmess_aead_encryptions(parser_factory):
    for enc in ["auto", "aes-128-gcm", "chacha20-poly1305", "none"]:
        inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", vmess_mode="aead", vmess_encryption=enc)
        url = ManualConfigBuilder.build(inp)
        p = assert_parses(url, parser_factory)
        if enc != "auto":
            assert p.encryption == enc

def test_vmess_legacy_transports(parser_factory):
    for net in ["raw", "websocket", "httpupgrade"]:
        inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", vmess_mode="legacy", network=net)
        url = ManualConfigBuilder.build(inp)
        p = assert_parses(url, parser_factory)
        
        expected_net = "raw" if net == "raw" else net
        if net == "ws": expected_net = "websocket"
        assert p.transport.network == expected_net

def test_vmess_legacy_rejects_reality():
    inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", vmess_mode="legacy", security="reality")
    with pytest.raises(ValueError, match="Reality is not supported for VMess Legacy"):
        ManualConfigBuilder.build(inp)

def test_vmess_legacy_rejects_unsupported_transports():
    for net in ["xhttp", "mkcp"]:
        inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", vmess_mode="legacy", network=net)
        with pytest.raises(ValueError, match="is not supported for VMess Legacy"):
            ManualConfigBuilder.build(inp)
    
    inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", vmess_mode="legacy", network="hysteria", security="tls")
    with pytest.raises(ValueError, match="is not supported for VMess Legacy"):
        ManualConfigBuilder.build(inp)

def test_encoding_vless_userinfo(parser_factory):
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="my@special:uuid/?&", security="none", network="raw")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "vless"

def test_encoding_vmess_aead_userinfo(parser_factory):
    inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="my@special:uuid/?&", vmess_mode="aead", security="none", network="raw")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "vmess"

def test_encoding_trojan_password(parser_factory):
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="my@special:pwd/?&", security="tls", network="raw")
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.protocol == "trojan"
    assert p.password == "my@special:pwd/?&"

def test_legacy_scy(parser_factory):
    inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", vmess_mode="legacy", network="raw", vmess_legacy_scy="chacha20-poly1305")
    url = ManualConfigBuilder.build(inp)
    assert "encryption=" not in url
    
    p = assert_parses(url, parser_factory)
    assert p.protocol == "vmess"

def test_query_encoding(parser_factory):
    inp = ManualConfigInput(
        protocol="vless", server="1.1.1.1", port=443, auth="uuid", 
        network="ws", security="tls", 
        path="/test?a=1&b=2%20#hash", 
        sni="ex.com/?=&#",
        fp="random#&="
    )
    url = ManualConfigBuilder.build(inp)
    
    p = assert_parses(url, parser_factory)
    assert p.transport.path == "/test?a=1&b=2%20#hash"
    assert p.tls.server_name == "ex.com/?=&#"
    
    inp = ManualConfigInput(
        protocol="vless", server="1.1.1.1", port=443, auth="uuid",
        network="raw", security="reality", pbk="base64==?&", sid="sid#1"
    )
    url = ManualConfigBuilder.build(inp)
    p = assert_parses(url, parser_factory)
    assert p.reality.public_key == "base64==?&"
    assert p.reality.short_id == "sid#1"

def test_vmess_legacy_rejects_grpc():
    from gui.builders.manual_config_builder import ManualConfigBuilder, ManualConfigInput
    import pytest
    inp = ManualConfigInput(protocol="vmess", server="1.1.1.1", port=443, auth="uuid", vmess_mode="legacy", network="grpc")
    with pytest.raises(ValueError, match="is not supported for VMess Legacy"):
        ManualConfigBuilder.build(inp)

def test_builder_reality_constraints():
    from gui.builders.manual_config_builder import ManualConfigBuilder, ManualConfigInput
    import pytest
    
    for net in ["ws", "websocket", "mkcp", "httpupgrade", "hysteria"]:
        inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network=net, security="reality", pbk="key")
        with pytest.raises(ValueError, match="Reality is not supported with network"):
            ManualConfigBuilder.build(inp)
            
    for net in ["raw", "xhttp", "grpc"]:
        inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network=net, security="reality", pbk="key")
        url = ManualConfigBuilder.build(inp)
        assert "reality" in url

def test_builder_hysteria_constraints():
    from gui.builders.manual_config_builder import ManualConfigBuilder, ManualConfigInput
    import pytest
    
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network="hysteria", security="none")
    with pytest.raises(ValueError, match="Hysteria requires TLS security"):
        ManualConfigBuilder.build(inp)
        
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network="hysteria", security="reality")
    with pytest.raises(ValueError, match="Reality is not supported with network hysteria"):
        ManualConfigBuilder.build(inp)
            
    inp = ManualConfigInput(protocol="vless", server="1.1.1.1", port=443, auth="uuid", network="hysteria", security="tls")
    url = ManualConfigBuilder.build(inp)
    assert "security=tls" in url

def test_trojan_security_none(parser_factory):
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="pwd", network="raw", security="none")
    url = ManualConfigBuilder.build(inp)
    assert "security=none" in url
    p = assert_parses(url, parser_factory)
    assert p.security_type == "none"

def test_trojan_security_tls(parser_factory):
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="pwd", network="raw", security="tls")
    url = ManualConfigBuilder.build(inp)
    assert "security=tls" in url
    p = assert_parses(url, parser_factory)
    assert p.security_type == "tls"

def test_trojan_reality_raw(parser_factory):
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="pwd", network="raw", security="reality", pbk="key")
    url = ManualConfigBuilder.build(inp)
    assert "security=reality" in url
    p = assert_parses(url, parser_factory)
    assert p.security_type == "reality"

def test_trojan_reality_grpc(parser_factory):
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="pwd", network="grpc", security="reality", pbk="key")
    url = ManualConfigBuilder.build(inp)
    assert "security=reality" in url
    p = assert_parses(url, parser_factory)
    assert p.security_type == "reality"

def test_trojan_invalid_reality_websocket(parser_factory):
    import pytest
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="pwd", network="ws", security="reality")
    with pytest.raises(ValueError, match="Reality is not supported with network ws"):
        ManualConfigBuilder.build(inp)

def test_trojan_invalid_hysteria_none(parser_factory):
    import pytest
    inp = ManualConfigInput(protocol="trojan", server="1.1.1.1", port=443, auth="pwd", network="hysteria", security="none")
    with pytest.raises(ValueError, match="Hysteria requires TLS security, got none"):
        ManualConfigBuilder.build(inp)

def test_trojan_uppercase_protocol_none_security(parser_factory):
    inp = ManualConfigInput(protocol="Trojan", server="1.1.1.1", port=443, auth="pwd", network="raw", security="none")
    url = ManualConfigBuilder.build(inp)
    assert "security=none" in url
    p = assert_parses(url, parser_factory)
    assert p.protocol == "trojan"
    assert p.security_type == "none"
