import pytest
from tests.parser.matrix.vless import VALID_VLESS_CASES, INVALID_VLESS_CASES
from parser.exceptions import ValidationError, ParseError

EXPECTED_ERRORS = {
    "ValidationError": ValidationError,
    "ParseError": ParseError
}

@pytest.mark.parametrize("case", VALID_VLESS_CASES, ids=lambda c: c["id"])
def test_vless_valid_matrix(case, parser_factory):
    config = parser_factory.parse_url(case["url"])
    assert config.protocol == "vless"
    assert config.server == case["expected_server"]
    assert config.port == case["expected_port"]
    assert config.transport.network == case["expected_network"]
    assert config.security_type == case["expected_security"]
    
    if "expected_remark" in case:
        assert config.remark == case["expected_remark"]
    if "expected_path" in case:
        assert config.transport.path == case["expected_path"]
    if "expected_sni" in case:
        assert getattr(config.tls, "server_name", None) == case["expected_sni"]

@pytest.mark.parametrize("case", INVALID_VLESS_CASES, ids=lambda c: c["id"])
def test_vless_invalid_matrix(case, parser_factory):
    err_cls = EXPECTED_ERRORS[case["error"]]
    match_str = case.get("match", "")
    with pytest.raises(err_cls, match=match_str):
        parser_factory.parse_url(case["url"])
