
VALID_VLESS_CASES = [
    {
        "id": "vless-tcp-none",
        "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=tcp&security=none#tcp_none",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_network": "raw",
        "expected_security": "none",
        "expected_remark": "tcp_none"
    },
    {
        "id": "vless-ws-tls",
        "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=ws&security=tls&sni=ex.com&path=%2Ffoo#ws_tls",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_network": "websocket",
        "expected_security": "tls",
        "expected_remark": "ws_tls",
        "expected_path": "/foo",
        "expected_sni": "ex.com"
    },
    {
        "id": "vless-reality-grpc",
        "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=grpc&security=reality&pbk=123&fp=firefox&serviceName=test#grpc_real",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_network": "grpc",
        "expected_security": "reality",
        "expected_remark": "grpc_real"
    }
]

INVALID_VLESS_CASES = [
    {
        "id": "vless-invalid-reality-ws",
        "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=ws&security=reality&pbk=123&fp=chrome",
        "error": "ValidationError",
        "match": "REALITY unsupported"
    },
    {
        "id": "vless-invalid-uuid",
        "url": "vless://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@1.2.3.4:443",
        "error": "ValidationError",
        "match": "Invalid VLESS UUID"
    },
    {
        "id": "vless-missing-port",
        "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4",
        "error": "ValidationError",
        "match": "Port is required"
    }
]

VALID_VLESS_CASES.append({
    "id": "vless-flow-xtls",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=tcp&security=tls&flow=xtls-rprx-vision",
    "expected_server": "1.2.3.4",
    "expected_port": 443,
    "expected_network": "raw",
    "expected_security": "tls"
})

VALID_VLESS_CASES.append({
    "id": "vless-mlkem-valid",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=mlkem768x25519plus.native.1rtt.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "expected_server": "1.2.3.4",
    "expected_port": 443,
    "expected_network": "raw",
    "expected_security": "none"
})

INVALID_VLESS_CASES.append({
    "id": "vless-invalid-flow",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?flow=invalid",
    "error": "ValidationError",
    "match": "Invalid VLESS flow"
})

INVALID_VLESS_CASES.append({
    "id": "vless-invalid-mlkem",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=mlkem768x25519plus",
    "error": "ValidationError",
    "match": "missing blocks"
})

INVALID_VLESS_CASES.append({
    "id": "vless-invalid-mlkem-handshake",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=invalid.native.1rtt.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "error": "ValidationError",
    "match": "Invalid VLESS ML-KEM handshake"
})

INVALID_VLESS_CASES.append({
    "id": "vless-invalid-mlkem-app",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=mlkem768x25519plus.invalid.1rtt.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "error": "ValidationError",
    "match": "Invalid VLESS ML-KEM appearance"
})

INVALID_VLESS_CASES.append({
    "id": "vless-invalid-mlkem-session",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=mlkem768x25519plus.native.invalid.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "error": "ValidationError",
    "match": "Invalid VLESS ML-KEM session"
})

INVALID_VLESS_CASES.append({
    "id": "vless-invalid-mlkem-padding",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=mlkem768x25519plus.native.1rtt.!!!!!!!!!!!!!!!!!!!!!!",
    "error": "ValidationError",
    "match": "Base64URL"
})

INVALID_VLESS_CASES.append({
    "id": "vless-invalid-mlkem-len",
    "url": "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=mlkem768x25519plus.native.1rtt.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "error": "ValidationError",
    "match": "decoded length"
})
