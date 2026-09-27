VALID_VMESS_CASES = [
    {
        "id": "vmess-aead-tcp",
        "url": "vmess://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=none&type=tcp#remark",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_uuid": "feb54431-301b-52bb-a6dd-e1e93e81bb9e",
        "expected_encryption": "none",
        "expected_network": "raw",
        "expected_remark": "remark",
        "expected_format": "vmess_aead_uri"
    },
    {
        "id": "vmess-legacy-json",
        "url": "vmess://eyJ2IjoiMiIsInBzIjoibGVnYWN5IiwiYWRkIjoiMS4yLjMuNCIsInBvcnQiOjQ0MywiaWQiOiJmZWI1NDQzMS0zMDFiLTUyYmItYTZkZC1lMWU5M2U4MWJiOWUiLCJhaWQiOiIwIiwic2N5IjoiYXV0byIsIm5ldCI6IndzIiwidGxzIjoidGxzIn0=",
        "expected_server": "1.2.3.4",
        "expected_port": 443,
        "expected_uuid": "feb54431-301b-52bb-a6dd-e1e93e81bb9e",
        "expected_encryption": "auto",
        "expected_network": "websocket",
        "expected_security": "tls",
        "expected_remark": "legacy",
        "expected_format": "vmess_legacy_json"
    }
]

INVALID_VMESS_CASES = [
    {
        "id": "vmess-aead-invalid-enc",
        "url": "vmess://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=garbage",
        "error": "ValidationError",
        "match": "Invalid VMess encryption"
    },
    {
        "id": "vmess-legacy-invalid-json",
        "url": "vmess://garbage_base64",
        "error": "ParseError",
        "match": "Invalid Base64 or JSON"
    }
]
