VALID_SHADOWSOCKS_CASES = [
    {
        "id": "ss-sip002",
        "url": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:443#remark",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_method": "aes-256-gcm",
        "expected_password": "password",
        "expected_remark": "remark",
        "expected_format": "shadowsocks_base64_userinfo"
    },
    {
        "id": "ss-legacy-b64",
        "url": "ss://YWVzLTEyOC1nY206cGFzc0AxLjIuMy40OjQ0Mw==#remark2",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_method": "aes-128-gcm",
        "expected_password": "pass",
        "expected_remark": "remark2",
        "expected_format": "shadowsocks_legacy_base64"
    },
    {
        "id": "ss-sip002-raw",
        "url": "ss://chacha20-poly1305:pass@1.2.3.4:443?uot=1#remark3",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_method": "chacha20-poly1305",
        "expected_password": "pass",
        "expected_remark": "remark3",
        "expected_format": "shadowsocks_sip002",
        "expected_uot": True
    }
]

INVALID_SHADOWSOCKS_CASES = [
    {
        "id": "ss-missing-method",
        "url": "ss://:pass@1.2.3.4:443",
        "error": "ValidationError",
        "match": "requires method and password"
    },
    {
        "id": "ss-invalid-structure",
        "url": "ss://garbage",
        "error": "ParseError",
        "match": "@ not found"
    }
]

VALID_SHADOWSOCKS_CASES.append({
    "id": "ss-ipv6",
    "url": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@[2001:db8::1]:443",
    "expected_server": "2001:db8::1",
    "expected_port": 443,
    "expected_method": "aes-256-gcm",
    "expected_password": "password",
    "expected_format": "shadowsocks_base64_userinfo"
})

VALID_SHADOWSOCKS_CASES.append({
    "id": "ss-plugin",
    "url": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:443?plugin=obfs-local",
    "expected_server": "1.2.3.4",
    "expected_port": 443,
    "expected_method": "aes-256-gcm",
    "expected_password": "password",
    "expected_format": "shadowsocks_base64_userinfo"
})

INVALID_SHADOWSOCKS_CASES.append({
    "id": "ss-invalid-ipv6",
    "url": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@2001:db8::1:443",
    "error": "ValidationError",
    "match": "Unbracketed IPv6"
})

INVALID_SHADOWSOCKS_CASES.append({
    "id": "ss-malformed-ipv6",
    "url": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@[2001:db8::1",
    "error": "ParseError",
    "match": "URL parsing failed: Invalid IPv6 URL"
})

INVALID_SHADOWSOCKS_CASES.append({
    "id": "ss-invalid-uot",
    "url": "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@1.2.3.4:443?uot=garbage",
    "error": "ValidationError",
    "match": "Invalid uot value"
})
