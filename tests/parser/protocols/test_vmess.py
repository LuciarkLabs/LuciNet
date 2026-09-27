import pytest
from tests.parser.matrix.vmess import VALID_VMESS_CASES, INVALID_VMESS_CASES
from parser.exceptions import ValidationError, ParseError

EXPECTED_ERRORS = {
    "ValidationError": ValidationError,
    "ParseError": ParseError
}

@pytest.mark.parametrize("case", VALID_VMESS_CASES, ids=lambda c: c["id"])
def test_vmess_valid_matrix(case, parser_factory):
    config = parser_factory.parse_url(case["url"])
    assert config.protocol == "vmess"
    assert config.server == case["expected_server"]
    assert config.port == case["expected_port"]
    assert config.user_id == case["expected_uuid"]
    assert config.encryption == case["expected_encryption"]
    assert config.transport.network == case["expected_network"]
    assert config.parse_meta.source_format == case["expected_format"]
    
    if "expected_remark" in case:
        assert config.remark == case["expected_remark"]
    if "expected_security" in case:
        assert config.security_type == case["expected_security"]

@pytest.mark.parametrize("case", INVALID_VMESS_CASES, ids=lambda c: c["id"])
def test_vmess_invalid_matrix(case, parser_factory):
    err_cls = EXPECTED_ERRORS[case["error"]]
    match_str = case.get("match", "")
    with pytest.raises(err_cls, match=match_str):
        parser_factory.parse_url(case["url"])
