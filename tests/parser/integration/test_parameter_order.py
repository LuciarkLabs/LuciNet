import pytest

def test_parameter_order_independence(parser_factory):
    url1 = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=tcp&security=tls&sni=ex.com&path=/foo&alpn=h2,http/1.1#remark"
    url2 = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?alpn=h2,http/1.1&path=/foo&security=tls&type=tcp&sni=ex.com#remark"
    
    config1 = parser_factory.parse_url(url1)
    config2 = parser_factory.parse_url(url2)
    
    assert config1.config_hash == config2.config_hash
    
    assert config1.connection_hash == config2.connection_hash
    
    assert config1.transport.network == config2.transport.network
    assert config1.tls.alpn == config2.tls.alpn
