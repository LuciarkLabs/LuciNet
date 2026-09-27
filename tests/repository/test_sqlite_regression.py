import pytest
import os
from domain.proxy import ProxyConfig
from repository.sqlite_repo import SQLiteProxyRepository

@pytest.mark.asyncio
async def test_sqlite_proxy_config_mapping(tmp_path):
    db_path = str(tmp_path / "test_mapping.db")
    repo = SQLiteProxyRepository(db_path=db_path)
    await repo.initialize()
    
    p = ProxyConfig(
        raw_url="vless://...",
        protocol="vless",
        remark="Test Proxy",
        server="1.1.1.1",
        port=443,
    )
    p.user_id = "test-uuid"
    p.sni = "example.com"
    p.security = "tls"
    p.network = "ws"
    p.flow = "xtls-rprx-vision"
    p.alpn = "h2,http/1.1"
    p.fingerprint = "chrome"
    p.path = "/graphql"
    p.host = "host.com"
    p.pbk = "public-key"
    p.sid = "session-id"
    p.spx = "/spx"
    p.country = "US"
    p.city = "New York"
    p.isp = "Cloudflare"
    p.real_ip = "1.1.1.2"
    p.ping = 150.5
    p.download_speed = 10.5
    p.status = "Valid"
    p.first_seen = 1000.0
    p.last_scan = 2000.0
    p.last_seen_alive = 2000.0
    p.scan_count = 5
    p.group_name = "MyGroup"
    p.sub_id = 123
    
    await repo.save(p)
    
    proxies = await repo.get_all()
    assert len(proxies) == 1
    
    saved_p = proxies[0]
    
    assert saved_p.protocol == "vless"
    assert saved_p.remark == "Test Proxy"
    assert saved_p.server == "1.1.1.1"
    assert saved_p.port == 443
    
    assert saved_p.user_id == "test-uuid"
    assert saved_p.uuid_pwd == "test-uuid"
    
    assert saved_p.sni == "example.com"
    assert saved_p.security == "tls"
    assert saved_p.network == "ws"
    assert saved_p.flow == "xtls-rprx-vision"
    assert saved_p.alpn == "h2,http/1.1"
    assert saved_p.fingerprint == "chrome"
    assert saved_p.path == "/graphql"
    assert saved_p.host == "host.com"
    assert saved_p.pbk == "public-key"
    assert saved_p.sid == "session-id"
    assert saved_p.spx == "/spx"
    assert saved_p.country == "US"
    assert saved_p.city == "New York"
    assert saved_p.isp == "Cloudflare"
    assert getattr(saved_p, "real_ip", "") == "1.1.1.2"
    assert saved_p.ping == 150.5
    assert saved_p.download_speed == 10.5
    assert saved_p.status == "Valid"
    assert saved_p.first_seen == 1000.0
    assert saved_p.last_scan == 2000.0
    assert saved_p.last_seen_alive == 2000.0
    assert saved_p.scan_count == 5
    assert saved_p.group_name == "MyGroup"
    assert saved_p.sub_id == 123
    
    assert saved_p.unique_hash == p.unique_hash
    
    saved_p.remark = "Updated Proxy"
    saved_p.ping = 120.0
    saved_p.real_ip = "1.1.1.3"
    saved_p.path = "/new-path"
    await repo.save(saved_p)
    
    updated_proxies = await repo.get_all()
    assert len(updated_proxies) == 1
    u_p = updated_proxies[0]
    assert u_p.remark == "Updated Proxy"
    assert u_p.ping == 120.0
    assert getattr(u_p, "real_ip", "") == "1.1.1.3"
    assert u_p.path == "/new-path"
    assert u_p.unique_hash == p.unique_hash
    
    await repo.delete(saved_p.id)
    assert len(await repo.get_all()) == 0
