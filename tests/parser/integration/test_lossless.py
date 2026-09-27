import pytest

def test_lossless_metadata_standard_uri(parser_factory):
    url = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=ws&security=tls&sni=ex.com&path=/foo#remark"
    config = parser_factory.parse_url(url)
    
    assert config.parse_meta.lossless is True
    assert len(config.parse_meta.unknown_params) == 0
    assert len(config.parse_meta.warnings) == 0

def test_lossless_metadata_with_deprecated_param(parser_factory):
    url = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=tcp&security=tls&allowInsecure=1#remark"
    config = parser_factory.parse_url(url)
    
    assert config.parse_meta.lossless is False
    assert any("allowInsecure" in w for w in config.parse_meta.warnings)

def test_lossless_metadata_with_invalid_finalmask(parser_factory):
    url = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?fm=invalidjson"
    config = parser_factory.parse_url(url)
    
    assert config.parse_meta.lossless is False
    assert config.finalmask_raw == "invalidjson"
    assert config.finalmask is None
