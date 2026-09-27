import pytest
from unittest.mock import patch
@pytest.fixture(autouse=True)
def mock_job_object():
    with patch("utils.win_job_object.assign_pid_to_job", return_value=True) as m:
        yield m

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from scanner.xray_runner import XrayRunnerPool
from domain.proxy import ProxyConfig
from domain.scan_result import ScanResult

class MockProcess:
    def __init__(self, returncode=None):
        self.pid = 12345
        self.returncode = returncode
        self.killed = False

    def kill(self):
        self.killed = True

    async def wait(self):
        if not self.killed and self.returncode is None:
            await asyncio.sleep(1000)
        return self.returncode

@pytest.fixture
def runner():
    pm = MagicMock()
    pm.get_free_port = AsyncMock(return_value=10800)
    pm.release_port = AsyncMock()
    pm.get_free_port.return_value = 10800
    
    chk = AsyncMock()
    chk.check_connection.return_value = ScanResult(status="Valid", latency_ms=100)
    
    rp = XrayRunnerPool(pm, chk)
    rp.set_concurrent_limit(5)
    return rp

@pytest.fixture
def proxy():
    p = ProxyConfig(raw_url="vless://id@1.1.1.1:443", protocol="vless", remark="Test", server="1.1.1.1", port=443)
    p.uuid_pwd = "id"
    return p

@pytest.mark.asyncio
async def test_xray_success(runner, proxy):
    mock_proc = MockProcess(returncode=None)
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(runner, "_wait_for_port", return_value=True):
            res = await runner.scan_proxy(proxy)
            
            assert res.status == "Valid"
            assert mock_proc.killed is True
            runner.port_manager.release_port.assert_called_with(10800)

@pytest.mark.asyncio
async def test_xray_startup_fail(runner, proxy):
    mock_proc = MockProcess(returncode=1)
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(runner, "_wait_for_port", return_value=False):
            res = await runner.scan_proxy(proxy)
            
            assert res.status == "Error"
            assert "exited with code 1" in res.error_message
            runner.port_manager.release_port.assert_called_with(10800)

@pytest.mark.asyncio
async def test_xray_readiness_timeout(runner, proxy):
    mock_proc = MockProcess(returncode=None)
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(runner, "_wait_for_port", return_value=False):
            res = await runner.scan_proxy(proxy)
            
            assert res.status == "Error"
            assert "Timeout" in res.error_message
            assert mock_proc.killed is True
            runner.port_manager.release_port.assert_called_with(10800)

@pytest.mark.asyncio
async def test_xray_cancellation(runner, proxy):
    mock_proc = MockProcess(returncode=None)

    async def slow_check(*args):
        await asyncio.sleep(10)

    runner.checker.check_connection = slow_check

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(runner, "_wait_for_port", return_value=True):
            task = asyncio.create_task(runner.scan_proxy(proxy))
            await asyncio.sleep(0.1)

            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            assert mock_proc.killed is True
            runner.port_manager.release_port.assert_called_with(10800)

@pytest.mark.asyncio
async def test_xray_unexpected_exit(runner, proxy):
    mock_proc = MockProcess(returncode=None)

    async def checking(*args):
        mock_proc.returncode = 1 
        return ScanResult(status="Valid")

    runner.checker.check_connection = checking

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(runner, "_wait_for_port", return_value=True):
            res = await runner.scan_proxy(proxy)
            runner.port_manager.release_port.assert_called_with(10800)

@pytest.mark.asyncio
async def test_xray_runner_assign_false(runner, proxy, mock_job_object):
    mock_job_object.return_value = False
    mock_proc = MockProcess(returncode=None)
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(runner, "_wait_for_port", return_value=True):
            res = await runner.scan_proxy(proxy)
            assert res.status == "Error"
            assert "Job assignment returned False" in res.error_message

@pytest.mark.asyncio
async def test_xray_runner_assign_raises(runner, proxy, mock_job_object):
    mock_job_object.side_effect = Exception("Kernel Panic")
    mock_proc = MockProcess(returncode=None)
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.object(runner, "_wait_for_port", return_value=True):
            res = await runner.scan_proxy(proxy)
            assert res.status == "Error"
            assert "Kernel Panic" in res.error_message

@pytest.mark.asyncio
async def test_parallel_runner_cancellation_isolation(runner, proxy):
    proc_a = MockProcess(returncode=None)
    proc_b = MockProcess(returncode=None)
    
    ports = [10801, 10802]
    runner.port_manager.get_free_port = AsyncMock(side_effect=ports)
    
    async def fake_spawn(*args, **kwargs):
        if not hasattr(fake_spawn, "called"):
            fake_spawn.called = True
            return proc_a
        return proc_b

    async def delayed_check(*args):
        await asyncio.sleep(0.5)
        return ScanResult(status="Valid")
    runner.checker.check_connection = delayed_check

    with patch("asyncio.create_subprocess_exec", side_effect=fake_spawn):
        with patch.object(runner, "_wait_for_port", return_value=True):
            task_a = asyncio.create_task(runner.scan_proxy(proxy))
            task_b = asyncio.create_task(runner.scan_proxy(proxy))
            await asyncio.sleep(0.1)

            task_a.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task_a

            assert proc_a.killed is True
            assert proc_b.killed is False

            res_b = await task_b
            assert res_b.status == "Valid"
            assert proc_b.killed is True
