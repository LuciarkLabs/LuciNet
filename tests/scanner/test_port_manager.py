import pytest
import asyncio
from scanner.port_manager import PortManager

@pytest.fixture
def port_manager():
    return PortManager(start_port=10800, max_ports=100)

@pytest.mark.asyncio
async def test_allocate_free_port(port_manager):
    port_manager._is_port_free_async = lambda p: asyncio.Future()
    port_manager._is_port_free_async = lambda p: _mock_free(p, True)
    
    port = await port_manager.get_free_port()
    assert port == 10800
    assert 10800 in port_manager._in_use
    
    await port_manager.release_port(10800)
    assert 10800 not in port_manager._in_use

@pytest.mark.asyncio
async def test_occupied_port(port_manager):
    async def mock_free(p):
        return p != 10800
        
    port_manager._is_port_free_async = mock_free
    
    port = await port_manager.get_free_port()
    assert port == 10801
    assert 10801 in port_manager._in_use
    assert 10800 not in port_manager._in_use

@pytest.mark.asyncio
async def test_concurrent_allocation(port_manager):
    port_manager._is_port_free_async = lambda p: _mock_free(p, True)
    
    tasks = [asyncio.create_task(port_manager.get_free_port()) for _ in range(50)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 50
    assert len(set(results)) == 50
    assert all(10800 <= p < 10850 for p in results)

@pytest.mark.asyncio
async def test_exhaustion(port_manager):
    port_manager._is_port_free_async = lambda p: _mock_free(p, False)
    
    with pytest.raises(RuntimeError, match="No free ports available"):
        await port_manager.get_free_port()

@pytest.mark.asyncio
async def test_reset_behavior(port_manager):
    port_manager._is_port_free_async = lambda p: _mock_free(p, True)
    
    p1 = await port_manager.get_free_port()
    assert p1 == 10800
    
    port_manager.reset()
    assert len(port_manager._in_use) == 0
    
    p2 = await port_manager.get_free_port()
    assert p2 == 10800

async def _mock_free(p, result):
    return result
