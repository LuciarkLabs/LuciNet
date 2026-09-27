import pytest
import asyncio
import base64
import aiohttp
from unittest.mock import patch

from domain.subscription import Subscription
from domain.models.proxy import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from repository.sqlite_repo import SQLiteProxyRepository
from services.subscription_service import SubscriptionService
from parser.factory import ParserFactory
from parser.json_detector import JsonDetector, JsonConfigType

class MockResponse:
    def __init__(self, text_data, status=200):
        self._text_data = text_data
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def text(self):
        return self._text_data

class MockSession:
    def __init__(self, mock_response=None, exc=None):
        self.mock_response = mock_response
        self.exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def get(self, url, **kwargs):
        if self.exc:
            raise self.exc
        return self.mock_response

def patch_aiohttp(text_data="", status=200, exc=None):
    if exc:
        session = MockSession(exc=exc)
    else:
        session = MockSession(mock_response=MockResponse(text_data, status))
    return patch("aiohttp.ClientSession", return_value=session)

async def create_repo(tmp_path):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_sub.db"))
    await repo.initialize()
    return repo

@pytest.mark.asyncio
async def test_proxy_subscription_update(tmp_path):
    repo = await create_repo(tmp_path)
    
    sub = Subscription(name="Sub1", url="http://sub.com")
    sub.last_update = 1000.0
    sub.id = await repo.save_subscription(sub)
    
    old_p = ProxyConfig(raw_url="vless://old", protocol="vless", remark="OldProxy")
    old_p.sub_id = sub.id
    await repo.save_many([old_p])
    
    old_r = RawXrayConfig(name="OldRaw", raw_payload="{}", sub_id=sub.id)
    await repo.save_raw_config(old_r)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    assert len(proxies) == 1
    assert len(raws) == 1
    
    service = SubscriptionService(repo, ParserFactory())
    
    new_data = "vless://new_uuid@1.1.1.1:443?encryption=none&security=none#NewProxy12345"
    
    with patch_aiohttp(text_data=new_data):
        success, count, msg = await service.fetch_and_update(sub)
        
    assert success is True
    assert count == 1
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert len(proxies_after) == 1
    assert proxies_after[0].remark == "NewProxy12345"
    assert len(raws_after) == 0

@pytest.mark.asyncio
async def test_raw_subscription_update(tmp_path):
    repo = await create_repo(tmp_path)
    
    sub = Subscription(name="Sub1", url="http://sub.com")
    sub.last_update = 1000.0
    sub.id = await repo.save_subscription(sub)
    
    old_p = ProxyConfig(raw_url="vless://old", protocol="vless", remark="OldProxy")
    old_p.sub_id = sub.id
    await repo.save_many([old_p])
    
    service = SubscriptionService(repo, ParserFactory())
    
    raw_json = '{"inbounds":[], "outbounds":[]}'
    
    with patch_aiohttp(text_data=raw_json):
        success, count, msg = await service.fetch_and_update(sub)
        
    assert success is True
    assert count == 1
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert len(proxies_after) == 0
    assert len(raws_after) == 1
    assert raws_after[0].raw_payload == raw_json

@pytest.mark.asyncio
async def test_atomic_rollback_proxy_insert_fails(tmp_path):
    repo = await create_repo(tmp_path)
    sub = Subscription(name="Sub1", url="http://sub.com")
    sub.last_update = 1000.0
    sub.id = await repo.save_subscription(sub)
    
    old_p = ProxyConfig(raw_url="vless://old", protocol="vless", remark="OldProxy")
    old_p.sub_id = sub.id
    await repo.save_many([old_p])
    
    old_r = RawXrayConfig(name="OldRaw", raw_payload="{}", sub_id=sub.id)
    await repo.save_raw_config(old_r)
    
    service = SubscriptionService(repo, ParserFactory())
    new_data = "vless://new_uuid@1.1.1.1:443?encryption=none&security=none#NewProxy12345"
    
    import aiosqlite
    original_connect = aiosqlite.connect
    class FailingConnection:
        def __init__(self, conn):
            self.conn = conn
        async def __aenter__(self):
            self.real_db = await self.conn.__aenter__()
            self.original_executemany = self.real_db.executemany
            async def executemany_hook(sql, parameters=None):
                if "INSERT INTO proxies" in sql:
                    raise RuntimeError("Injected Insert Proxy Failure")
                return await self.original_executemany(sql, parameters)
            self.real_db.executemany = executemany_hook
            return self.real_db
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.conn.__aexit__(exc_type, exc_val, exc_tb)

    def failing_connect(*args, **kwargs):
        conn = original_connect(*args, **kwargs)
        return FailingConnection(conn)
        
    with patch("repository.sqlite_repo.aiosqlite.connect", side_effect=failing_connect):
        with patch_aiohttp(text_data=new_data):
            success, count, msg = await service.fetch_and_update(sub)
            
    assert success is False
    assert "Injected Insert Proxy Failure" in msg
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert len(proxies_after) == 1
    assert proxies_after[0].remark == "OldProxy"
    
    subs_after = await repo.get_subscriptions()
    assert subs_after[0].last_update == 1000.0
    assert len(raws_after) == 1
    assert raws_after[0].name == "OldRaw"
    
    subs_after = await repo.get_subscriptions()
    assert subs_after[0].last_update == 1000.0

@pytest.mark.asyncio
async def test_atomic_rollback_raw_insert_fails(tmp_path):
    repo = await create_repo(tmp_path)
    sub = Subscription(name="Sub1", url="http://sub.com")
    sub.last_update = 1000.0
    sub.id = await repo.save_subscription(sub)
    
    old_p = ProxyConfig(raw_url="vless://old", protocol="vless", remark="OldProxy")
    old_p.sub_id = sub.id
    await repo.save_many([old_p])
    
    service = SubscriptionService(repo, ParserFactory())
    raw_json = '{"inbounds":[], "outbounds":[]}'
    
    import aiosqlite
    original_connect = aiosqlite.connect
    class FailingConnection:
        def __init__(self, conn):
            self.conn = conn
        async def __aenter__(self):
            self.real_db = await self.conn.__aenter__()
            self.original_execute = self.real_db.execute
            async def execute_hook(sql, parameters=None):
                if "INSERT INTO xray_raw_configs" in sql:
                    raise RuntimeError("Injected Insert Raw Failure")
                return await self.original_execute(sql, parameters)
            self.real_db.execute = execute_hook
            return self.real_db
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.conn.__aexit__(exc_type, exc_val, exc_tb)

    def failing_connect(*args, **kwargs):
        conn = original_connect(*args, **kwargs)
        return FailingConnection(conn)
        
    with patch("repository.sqlite_repo.aiosqlite.connect", side_effect=failing_connect):
        with patch_aiohttp(text_data=raw_json):
            success, count, msg = await service.fetch_and_update(sub)
            
    assert success is False
    assert "Injected Insert Raw Failure" in msg
    
    proxies_after = await repo.get_all()
    assert len(proxies_after) == 1
    assert proxies_after[0].remark == "OldProxy"
    
    subs_after = await repo.get_subscriptions()
    assert subs_after[0].last_update == 1000.0

@pytest.mark.asyncio
async def test_atomic_rollback_cleanup_fails(tmp_path):
    repo = await create_repo(tmp_path)
    
    sub = Subscription(name="Sub1", url="http://sub.com")
    sub.last_update = 1000.0
    sub.last_update = 1000.0
    sub.id = await repo.save_subscription(sub)
    
    old_p = ProxyConfig(raw_url="vless://old", protocol="vless", remark="OldProxy")
    old_p.sub_id = sub.id
    await repo.save_many([old_p])
    
    old_r = RawXrayConfig(name="OldRaw", raw_payload="{}", sub_id=sub.id)
    await repo.save_raw_config(old_r)
    
    service = SubscriptionService(repo, ParserFactory())
    new_data = "vless://new_uuid@1.1.1.1:443?encryption=none&security=none#NewProxy12345"
    
    import aiosqlite
    original_connect = aiosqlite.connect
    class FailingConnection:
        def __init__(self, conn):
            self.conn = conn
        async def __aenter__(self):
            self.real_db = await self.conn.__aenter__()
            self.original_execute = self.real_db.execute
            async def execute_hook(sql, parameters=None):
                if "DELETE FROM proxies" in sql:
                    raise RuntimeError("Injected Cleanup Failure")
                return await self.original_execute(sql, parameters)
            self.real_db.execute = execute_hook
            return self.real_db
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.conn.__aexit__(exc_type, exc_val, exc_tb)

    def failing_connect(*args, **kwargs):
        conn = original_connect(*args, **kwargs)
        return FailingConnection(conn)
        
    with patch("repository.sqlite_repo.aiosqlite.connect", side_effect=failing_connect):
        with patch_aiohttp(text_data=new_data):
            success, count, msg = await service.fetch_and_update(sub)
            
    assert success is False
    assert "Injected Cleanup Failure" in msg
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert len(proxies_after) == 1
    assert proxies_after[0].remark == "OldProxy"
    
    subs_after = await repo.get_subscriptions()
    assert subs_after[0].last_update == 1000.0
    
    assert len(raws_after) == 1
    assert raws_after[0].name == "OldRaw"
    
    subs_after = await repo.get_subscriptions()
    assert subs_after[0].last_update == 1000.0
    
    
    subs_after = await repo.get_subscriptions()
    assert len(subs_after) == 1
    assert subs_after[0].last_update == 1000.0

@pytest.mark.asyncio
async def test_network_base64(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    data = "vless://new_uuid@1.1.1.1:443?encryption=none&security=none#P1\nvmess://eyJ2IjoiMiIsInBzIjoiUDIiLCJhZGQiOiIxLjEuMS4xIiwicG9ydCI6IjQ0MyIsImlkIjoidXVpZCJ9"
    b64_data = base64.b64encode(data.encode('utf-8')).decode('utf-8')
    
    with patch_aiohttp(text_data=b64_data):
        success, count, msg = await service.fetch_and_update(sub)
    
    assert success is True
    assert count == 2
    
@pytest.mark.asyncio
async def test_network_invalid(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    with patch_aiohttp(text_data="random garbage data"):
        success, count, msg = await service.fetch_and_update(sub)
    
    assert success is False
    assert count == 0
    
@pytest.mark.asyncio
async def test_network_client_error(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    with patch_aiohttp(exc=aiohttp.ClientError("DNS Error")):
        success, count, msg = await service.fetch_and_update(sub)
    
    assert success is False
    assert count == 0
    
@pytest.mark.asyncio
async def test_network_non_200(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    with patch_aiohttp(text_data="", status=404):
        success, count, msg = await service.fetch_and_update(sub)
    
    assert success is False
    assert count == 0
    assert "404" in msg

@pytest.mark.asyncio
async def test_unsupported_json_types_fallback(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    single_outbound = '{"protocol":"vless", "settings":{}}'
    with patch_aiohttp(text_data=single_outbound):
        success, count, msg = await service.fetch_and_update(sub)
        
    assert success is False
    assert count == 0
    
    outbound_array = '[{"protocol":"vless", "settings":{}}]'
    with patch_aiohttp(text_data=outbound_array):
        success, count, msg = await service.fetch_and_update(sub)
        
    assert success is False
    assert count == 0



@pytest.mark.asyncio
async def test_atomic_rollback_subscription_save_fails(tmp_path):
    repo = await create_repo(tmp_path)
    
    sub = Subscription(name="Sub1", url="http://sub.com")
    sub.last_update = 1000.0
    sub.id = await repo.save_subscription(sub)
    
    old_p = ProxyConfig(raw_url="vless://old", protocol="vless", remark="OldProxy")
    old_p.sub_id = sub.id
    await repo.save_many([old_p])
    
    old_r = RawXrayConfig(name="OldRaw", raw_payload="{}", sub_id=sub.id)
    await repo.save_raw_config(old_r)
    
    service = SubscriptionService(repo, ParserFactory())
    new_data = "vless://new_uuid@1.1.1.1:443?encryption=none&security=none#NewProxy"
    
    import aiosqlite
    original_connect = aiosqlite.connect
    class FailingConnection:
        def __init__(self, conn):
            self.conn = conn
        async def __aenter__(self):
            self.real_db = await self.conn.__aenter__()
            self.original_execute = self.real_db.execute
            async def execute_hook(sql, parameters=None):
                if "UPDATE subscriptions" in sql:
                    raise RuntimeError("Injected Subscription Save Failure")
                return await self.original_execute(sql, parameters)
            self.real_db.execute = execute_hook
            return self.real_db
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.conn.__aexit__(exc_type, exc_val, exc_tb)

    def failing_connect(*args, **kwargs):
        conn = original_connect(*args, **kwargs)
        return FailingConnection(conn)
        
    with patch("repository.sqlite_repo.aiosqlite.connect", side_effect=failing_connect):
        with patch_aiohttp(text_data=new_data):
            success, count, msg = await service.fetch_and_update(sub)
            
    assert success is False
    assert "Injected Subscription Save Failure" in msg
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert len(proxies_after) == 1
    assert proxies_after[0].remark == "OldProxy"
    assert len(raws_after) == 1
    assert raws_after[0].name == "OldRaw"
    
    subs_after = await repo.get_subscriptions()
    assert subs_after[0].last_update == 1000.0


@pytest.mark.asyncio
async def test_input_empty_content(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    with patch_aiohttp(text_data=""):
        success, count, msg = await service.fetch_and_update(sub)
    
    assert success is False
    assert count == 0

@pytest.mark.asyncio
async def test_input_malformed_base64(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    with patch_aiohttp(text_data="!@#malformed---"):
        success, count, msg = await service.fetch_and_update(sub)
    
    assert success is False
    assert count == 0

@pytest.mark.asyncio
async def test_input_trojan(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    data = "trojan://password@1.1.1.1:443#TrojanNode"
    with patch_aiohttp(text_data=data):
        success, count, msg = await service.fetch_and_update(sub)
    
    assert success is True
    assert count == 1

@pytest.mark.asyncio
async def test_input_shadowsocks(tmp_path):
    repo = await create_repo(tmp_path)
    service = SubscriptionService(repo, ParserFactory())
    sub = Subscription(name="Sub1", url="http://sub.com")
    
    b64_part = base64.urlsafe_b64encode(b"chacha20-ietf-poly1305:password").decode('utf-8')
    data = f"ss://{b64_part}@1.1.1.1:443#SSNode"
    with patch_aiohttp(text_data=data):
        success, count, msg = await service.fetch_and_update(sub)
    
    assert success is True
    assert count == 1

