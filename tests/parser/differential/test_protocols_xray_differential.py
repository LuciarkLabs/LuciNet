import pytest
import os
from parser.factory import ParserFactory
from parser.exceptions import ValidationError, ParseError
from tests.parser.differential.schemas import load_vectors
from tests.parser.differential.reference.runner import run_go_reference
from tests.parser.differential.reference.canonicalize import canonicalize_go_xray_json

EXPECTED_ERRORS = {
    "ValidationError": ValidationError,
    "ParseError": ParseError,
    "parse": (ValidationError, ParseError),
}

def _get_vectors(filename):
    path = os.path.join(os.path.dirname(__file__), 'vectors', filename)
    return load_vectors(path)

PROTOCOLS = [
    ("vless", _get_vectors("vless.json")),
    ("vmess_aead", _get_vectors("vmess_aead.json")),
    ("trojan", _get_vectors("trojan.json")),
    ("shadowsocks", _get_vectors("shadowsocks.json")),
]

FLATTENED_VECTORS = []
for proto, vectors in PROTOCOLS:
    for vector in vectors:
        FLATTENED_VECTORS.append((proto, vector))

@pytest.fixture
def parser_factory():
    return ParserFactory()

@pytest.mark.parametrize("proto, vector", FLATTENED_VECTORS, ids=[v["id"] for p, v in FLATTENED_VECTORS])
def test_xray_protocols_golden_differential(parser_factory, proto, vector):
    go_success, go_result = run_go_reference(vector["input"])
    
    if not go_success:
        go_error_category = go_result
        
        if go_error_category not in EXPECTED_ERRORS:
            pytest.fail(f"Unknown oracle error kind: {go_error_category}")
            
        expected_py_err = EXPECTED_ERRORS[go_error_category]
        
        with pytest.raises(expected_py_err):
            parser_factory.parse_url(vector["input"])
        print(f"\nLIVE ORACLE FAIL EXPECTED AND MATCHED: {vector['id']}")
            
    else:
        canonical_go = canonicalize_go_xray_json(go_result)
        
        py_config = parser_factory.parse_url(vector["input"])
        
        assert py_config.protocol == canonical_go["protocol"]
        assert py_config.server == canonical_go["server"]
        assert py_config.port == canonical_go["port"]
        
        if "user_id" in canonical_go:
            assert py_config.user_id == canonical_go["user_id"]
        if "password" in canonical_go:
            assert py_config.password == canonical_go["password"]
        if "method" in canonical_go:
            assert py_config.method == canonical_go["method"]
            
        assert py_config.transport.network == canonical_go["network"]
        assert py_config.security_type == canonical_go["security_type"]
        
        if "sni" in canonical_go:
            assert py_config.tls.server_name == canonical_go["sni"]
        if "fp" in canonical_go:
            assert py_config.tls.fingerprint == canonical_go["fp"]
        if "pbk" in canonical_go:
            assert py_config.reality.public_key == canonical_go["pbk"]
        if "grpc_service_name" in canonical_go:
            assert py_config.transport.grpc_service_name == canonical_go["grpc_service_name"]
        if "path" in canonical_go:
            assert py_config.transport.path == canonical_go["path"]
        print(f"\nLIVE ORACLE PASS EXACT MATCH: {vector['id']}")
