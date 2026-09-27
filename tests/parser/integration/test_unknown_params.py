import pytest

def test_unknown_params_preservation(parser_factory):
    url = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=tcp&security=tls&mycustomplugin=enabled"
    
    config = parser_factory.parse_url(url)
    
    assert "mycustomplugin" in config.parse_meta.unknown_params
    assert config.parse_meta.unknown_params["mycustomplugin"] == "enabled"
    
    assert config.protocol == "vless"
    assert config.transport.network == "raw"
    assert config.security_type == "tls"
    
    assert config.parse_meta.lossless is False

def test_legacy_vmess_unknown_params(parser_factory):
    b64 = "eyJ2IjoiMiIsInBzIjoidGVzdCIsImFkZCI6IjEuMi4zLjQiLCJwb3J0Ijo0NDMsImlkIjoiZmViNTQ0MzEtMzAxYi01MmJiLWE2ZGQtZTFlOTNlODFiYjllIiwidW5rbm93bl9rZXkiOiIxMjMifQ=="
    url = f"vmess://{b64}"
    
    config = parser_factory.parse_url(url)
    assert config.parse_meta.extensions["legacy_unknown_unknown_key"] == "123"
    assert config.parse_meta.lossless is False
