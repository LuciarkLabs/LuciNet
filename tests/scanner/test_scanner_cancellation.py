import pytest
import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock
from services.scan_service import ScanService
from domain.proxy import ProxyConfig

@pytest.mark.asyncio
async def test_cross_thread_cancellation_and_second_scan():
    repo = AsyncMock()
    runner = MagicMock()
    
    scan_call_count = 0
    
    async def slow_scan(*args):
        nonlocal scan_call_count
        scan_call_count += 1
        await asyncio.sleep(5)
        return AsyncMock(status="Valid")
    
    runner.scan_proxy = slow_scan
    
    service = ScanService(runner, repo)
    proxies = [ProxyConfig(raw_url=f"vless://{i}", protocol="vless", remark=str(i)) for i in range(100)]
    
    def run_in_bg(loop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(service.scan_all(proxies, lambda p, m: None, concurrent_scans=10))

    bg_loop = asyncio.new_event_loop()
    t = threading.Thread(target=run_in_bg, args=(bg_loop,))
    t.start()
    
    await asyncio.sleep(0.5)
    
    assert hasattr(service, '_loop')
    assert service._loop is bg_loop
    
    service.cancel()
    
    t.join(timeout=3)
    assert not t.is_alive()
    
    assert service.current_queue.empty()
    assert service.is_cancelled is True
    assert service._loop is None
    repo.save_many.assert_called_once()
    assert scan_call_count > 0
    
    repo.save_many.reset_mock()
    scan_call_count = 0
    
    async def fast_scan(*args):
        nonlocal scan_call_count
        scan_call_count += 1
        return AsyncMock(status="Valid")
    runner.scan_proxy = fast_scan
    
    bg_loop2 = asyncio.new_event_loop()
    t2 = threading.Thread(target=run_in_bg, args=(bg_loop2,))
    t2.start()
    
    t2.join(timeout=3)
    assert not t2.is_alive()
    
    assert scan_call_count == 100
    assert service.current_queue.empty()
    repo.save_many.assert_called_once()
