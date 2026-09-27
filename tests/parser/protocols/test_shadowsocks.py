import pytest
from tests.parser.matrix.shadowsocks import VALID_SHADOWSOCKS_CASES, INVALID_SHADOWSOCKS_CASES
from parser.exceptions import ValidationError, ParseError

EXPECTED_ERRORS = {
    "ValidationError": ValidationError,
    "ParseError": ParseError
}

@pytest.mark.parametrize("case", VALID_SHADOWSOCKS_CASES, ids=lambda c: c["id"])
def test_shadowsocks_valid_matrix(case, parser_factory):
    config = parser_factory.parse_url(case["url"])
    assert config.protocol == "shadowsocks"
    assert config.server == case["expected_server"]
    assert config.port == int(case["expected_port"])
    assert config.method == case["expected_method"]
    assert config.password == case["expected_password"]
    assert config.parse_meta.source_format == case["expected_format"]
    
    if "expected_remark" in case:
        assert config.remark == case["expected_remark"]
    if "expected_uot" in case:
        assert config.ss_uot == case["expected_uot"]

@pytest.mark.parametrize("case", INVALID_SHADOWSOCKS_CASES, ids=lambda c: c["id"])
def test_shadowsocks_invalid_matrix(case, parser_factory):
    err_cls = EXPECTED_ERRORS[case["error"]]
    match_str = case.get("match", "")
    with pytest.raises(err_cls, match=match_str):
        parser_factory.parse_url(case["url"])
