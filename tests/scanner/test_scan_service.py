import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from services.scan_service import ScanService
from domain.proxy import ProxyConfig
from domain.scan_result import ScanResult

@pytest.fixture
def repo():
    return AsyncMock()

@pytest.fixture
def runner():
    r = MagicMock()
    r.checker = MagicMock()
    return r

@pytest.mark.asyncio
async def test_scan_all_concurrency(repo, runner):
    service = ScanService(runner, repo)
    proxies = [ProxyConfig(raw_url=f"test://{i}", protocol="test", remark=str(i)) for i in range(20)]
    
    active_count = 0
    max_active = 0
    
    async def mock_scan_proxy(proxy):
        nonlocal active_count, max_active
        active_count += 1
        max_active = max(max_active, active_count)
        await asyncio.sleep(0.01)
        active_count -= 1
        return ScanResult(status="Valid", latency_ms=10)
        
    runner.scan_proxy = mock_scan_proxy
    
    await service.scan_all(proxies, on_progress=lambda p, m: None, concurrent_scans=5)
    
    assert max_active == 5
    assert repo.save_many.call_count == 1

@pytest.mark.asyncio
async def test_worker_exception_handling(repo, runner):
    service = ScanService(runner, repo)
    proxies = [ProxyConfig(raw_url=f"test://{i}", protocol="test", remark=str(i)) for i in range(10)]
    
    call_count = 0
    async def faulty_scan_proxy(proxy):
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            raise RuntimeError("Intentional Worker Crash")
        return ScanResult(status="Valid", latency_ms=10)
        
    runner.scan_proxy = faulty_scan_proxy
    
    await service.scan_all(proxies, on_progress=lambda p, m: None, concurrent_scans=2)
    
    assert call_count == 10
    repo.save_many.assert_called_once()

@pytest.mark.asyncio
async def test_db_failure_handling(repo, runner):
    service = ScanService(runner, repo)
    proxies = [ProxyConfig(raw_url="test://1", protocol="test", remark="1")]
    
    async def mock_scan(proxy):
        return ScanResult(status="Valid", latency_ms=10)
    runner.scan_proxy = mock_scan
    
    repo.save_many.side_effect = Exception("DB save failed!")
    
    try:
        await service.scan_all(proxies, on_progress=lambda p, m: None)
    except Exception:
        pass
    
    assert getattr(service, '_loop', None) is None

@pytest.mark.asyncio
async def test_large_queue_cancellation(repo, runner):
    service = ScanService(runner, repo)
    proxies = [ProxyConfig(raw_url=f"test://{i}", protocol="test", remark=str(i)) for i in range(1000)]
    
    async def block_scan(proxy):
        await asyncio.sleep(5)
        return ScanResult(status="Valid", latency_ms=10)
    runner.scan_proxy = block_scan
    
    task = asyncio.create_task(service.scan_all(proxies, on_progress=lambda p, m: None, concurrent_scans=10))
    await asyncio.sleep(0.1)
    
    assert not service.current_queue.empty()
    
    service.cancel()
    await task
    
    assert service.current_queue.empty()
    assert getattr(service, '_loop', None) is None
