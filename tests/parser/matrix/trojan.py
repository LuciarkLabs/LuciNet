VALID_TROJAN_CASES = [
    {
        "id": "trojan-tls-tcp",
        "url": "trojan://password@1.2.3.4:443?type=tcp&security=tls&sni=ex.com#remark",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_password": "password",
        "expected_network": "raw",
        "expected_security": "tls",
        "expected_remark": "remark",
        "expected_sni": "ex.com"
    },
    {
        "id": "trojan-reality-grpc",
        "url": "trojan://pass@1.2.3.4:443?type=grpc&security=reality&pbk=123&fp=chrome&serviceName=svc#rem",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_password": "pass",
        "expected_network": "grpc",
        "expected_security": "reality",
        "expected_remark": "rem",
        "expected_pbk": "123"
    }
]

INVALID_TROJAN_CASES = [
    {
        "id": "trojan-missing-password",
        "url": "trojan://@1.2.3.4:443?type=tcp&security=tls",
        "error": "ValidationError",
        "match": "Trojan requires password"
    }
]
