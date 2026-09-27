import pytest
from tests.parser.differential.reference.canonicalize import canonicalize_go_xray_json

def test_canonicalize_go_xray_json_valid():
    go_json = {
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "address": "1.2.3.4",
                "port": 443,
                "id": "uuid-1234"
            },
            "streamSettings": {
                "network": "raw",
                "security": "reality",
                "realitySettings": {
                    "serverName": "example.com",
                    "fingerprint": "chrome",
                    "password": "pbk123"
                }
            },
            "tag": "My VLESS"
        }]
    }
    
    canonical = canonicalize_go_xray_json(go_json)
    
    assert canonical["protocol"] == "vless"
    assert canonical["server"] == "1.2.3.4"
    assert canonical["port"] == 443
    assert canonical["user_id"] == "uuid-1234"
    assert canonical["network"] == "raw"
    assert canonical["security_type"] == "reality"
    assert canonical["sni"] == "example.com"
    assert canonical["fp"] == "chrome"
    assert canonical["pbk"] == "pbk123"
    assert canonical["remark"] == "My VLESS"

def test_canonicalize_go_xray_json_missing_fields():
    go_json = {
        "outbounds": [{
            "protocol": "vless"
        }]
    }
    with pytest.raises(ValueError, match="Failed to extract required field"):
        canonicalize_go_xray_json(go_json)

def test_canonicalize_go_xray_json_shadowsocks():
    go_json = {
        "outbounds": [{
            "protocol": "shadowsocks",
            "settings": {
                "address": "1.2.3.4",
                "port": 443,
                "method": "aes-256-gcm",
                "password": "pass"
            },
            "streamSettings": {
                "network": "raw",
                "security": "none"
            }
        }]
    }
    canonical = canonicalize_go_xray_json(go_json)
    
    assert canonical["protocol"] == "shadowsocks"
    assert canonical["server"] == "1.2.3.4"
    assert canonical["port"] == 443
    assert canonical["method"] == "aes-256-gcm"
    assert canonical["password"] == "pass"
    assert canonical["network"] == "raw"
    assert canonical["security_type"] == "none"
