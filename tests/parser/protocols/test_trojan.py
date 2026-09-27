import pytest
from tests.parser.matrix.trojan import VALID_TROJAN_CASES, INVALID_TROJAN_CASES
from parser.exceptions import ValidationError, ParseError

EXPECTED_ERRORS = {
    "ValidationError": ValidationError,
    "ParseError": ParseError
}

@pytest.mark.parametrize("case", VALID_TROJAN_CASES, ids=lambda c: c["id"])
def test_trojan_valid_matrix(case, parser_factory):
    config = parser_factory.parse_url(case["url"])
    assert config.protocol == "trojan"
    assert config.server == case["expected_server"]
    assert config.port == case["expected_port"]
    assert config.password == case["expected_password"]
    assert config.transport.network == case["expected_network"]
    assert config.security_type == case["expected_security"]
    
    if "expected_remark" in case:
        assert config.remark == case["expected_remark"]
    if "expected_sni" in case:
        assert config.tls.server_name == case["expected_sni"]
    if "expected_pbk" in case:
        assert config.reality.password == case["expected_pbk"]

@pytest.mark.parametrize("case", INVALID_TROJAN_CASES, ids=lambda c: c["id"])
def test_trojan_invalid_matrix(case, parser_factory):
    err_cls = EXPECTED_ERRORS[case["error"]]
    match_str = case.get("match", "")
    with pytest.raises(err_cls, match=match_str):
        parser_factory.parse_url(case["url"])
