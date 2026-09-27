import pytest

def test_parse_determinism(parser_factory):
    url = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=grpc&security=reality&pbk=123&fp=chrome&serviceName=test#my_remark"
    
    config1 = parser_factory.parse_url(url)
    config2 = parser_factory.parse_url(url)
    
    assert config1.config_hash == config2.config_hash
    assert config1.parse_meta.source_format == "vless_uri"

def test_vmess_cross_format_semantic_equivalence(parser_factory):
    b64 = "eyJ2IjoiMiIsImFkZCI6IjEuMi4zLjQiLCJwb3J0Ijo0NDMsImlkIjoiZmViNTQ0MzEtMzAxYi01MmJiLWE2ZGQtZTFlOTNlODFiYjllIiwic2N5IjoiYXV0byJ9"
    url_legacy = f"vmess://{b64}"
    
    url_aead = "vmess://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?encryption=auto&type=tcp"
    
    config_legacy = parser_factory.parse_url(url_legacy)
    config_aead = parser_factory.parse_url(url_aead)
    
    assert config_legacy.config_hash == config_aead.config_hash
