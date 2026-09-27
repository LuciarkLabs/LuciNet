import pytest
from parser.transport import populate_transport
from domain.models import ProxyConfig
from parser.exceptions import ValidationError

def get_base_config():
    return ProxyConfig(raw_url="", protocol="vless", server="1.1.1.1", port=443)

def test_transport_raw():
    c = get_base_config()
    consumed = populate_transport(c, {"type": "tcp", "headerType": "none"})
    assert "type" in consumed
    assert c.transport.network == "raw"

def test_transport_websocket():
    c = get_base_config()
    consumed = populate_transport(c, {"type": "ws", "path": "/foo", "host": "ex.com"})
    assert c.transport.network == "websocket"
    assert c.transport.path == "/foo"
    assert c.transport.host == "ex.com"

def test_transport_websocket_empty_path():
    c = get_base_config()
    with pytest.raises(ValidationError, match="empty path"):
        populate_transport(c, {"type": "ws", "path": ""})

def test_transport_mkcp():
    c = get_base_config()
    consumed = populate_transport(c, {"type": "kcp", "headerType": "wechat-video", "seed": "test", "mtu": "1350", "tti": "50"})
    assert c.transport.network == "mkcp"
    assert c.transport.kcp_mtu == 1350
    assert c.transport.kcp_tti == 50
    assert "headerType" not in consumed
    assert "seed" not in consumed

def test_transport_mkcp_invalid():
    c = get_base_config()
    with pytest.raises(ValidationError, match="invalid mkcp mtu"):
        populate_transport(c, {"type": "kcp", "mtu": "abc"})
    with pytest.raises(ValidationError, match="invalid mkcp tti"):
        populate_transport(c, {"type": "kcp", "tti": "abc"})

def test_transport_xhttp():
    c = get_base_config()
    consumed = populate_transport(c, {"type": "splithttp", "host": "ex.com", "path": "/", "mode": "auto", "extra": "e"})
    assert c.transport.network == "xhttp"
    assert c.transport.xhttp_mode == "auto"
    assert c.transport.xhttp_extra == "e"

def test_transport_grpc():
    c = get_base_config()
    consumed = populate_transport(c, {"type": "grpc", "serviceName": "Service", "mode": "multi", "authority": "auth"})
    assert c.transport.network == "grpc"
    assert c.transport.grpc_mode == "multi"
    assert c.transport.grpc_authority == "auth"

def test_transport_grpc_default_mode():
    c = get_base_config()
    consumed = populate_transport(c, {"type": "grpc", "serviceName": "Service"})
    assert c.transport.network == "grpc"
    assert c.transport.grpc_mode == "gun"

def test_transport_grpc_invalid():
    c = get_base_config()
    with pytest.raises(ValidationError, match="empty"):
        populate_transport(c, {"type": "grpc", "serviceName": ""})
    with pytest.raises(ValidationError, match="empty"):
        populate_transport(c, {"type": "grpc", "serviceName": "s", "mode": ""})
    with pytest.raises(ValidationError, match="Invalid"):
        populate_transport(c, {"type": "grpc", "serviceName": "s", "mode": "invalid"})

def test_transport_httpupgrade():
    c = get_base_config()
    populate_transport(c, {"type": "httpupgrade", "host": "ex.com"})
    assert c.transport.network == "httpupgrade"
    assert c.transport.path == "/"

def test_transport_hysteria():
    c = get_base_config()
    populate_transport(c, {"type": "hysteria"})
    assert c.transport.network == "hysteria"

def test_transport_empty_explicit():
    c = get_base_config()
    with pytest.raises(ValidationError, match="empty"):
        populate_transport(c, {"type": ""})

def test_transport_empty_fallback():
    c = get_base_config()
    consumed = populate_transport(c, {}, default_net="tcp")
    assert c.transport.network == "raw"

def test_transport_invalid():
    c = get_base_config()
    with pytest.raises(ValidationError):
        populate_transport(c, {"type": "TCP"})

def test_transport_unsupported():
    c = get_base_config()
    with pytest.raises(ValidationError):
        populate_transport(c, {"type": "quic"})
