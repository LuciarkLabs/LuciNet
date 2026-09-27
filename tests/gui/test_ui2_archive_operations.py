from PySide6.QtWidgets import QApplication
import sys
app = QApplication.instance() or QApplication(sys.argv)
import pytest
from unittest.mock import MagicMock
import asyncio

from domain.proxy import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from repository.sqlite_repo import SQLiteProxyRepository
from gui.tabs.archive.managers.tools_manager import ToolsManager

import gui.workers
class MockAsyncTaskWorker(gui.workers.AsyncTaskWorker):
    def __init__(self, coro):
        super().__init__(coro)
        self.coro = coro
        
    def start(self):
        async def run():
            try:
                res = await self.coro
                self.finished_signal.emit(res)
            except Exception as e:
                self.error_signal.emit(str(e))
        asyncio.create_task(run())

gui.workers.AsyncTaskWorker = MockAsyncTaskWorker
gui.tabs.archive.managers.tools_manager.AsyncTaskWorker = MockAsyncTaskWorker

@pytest.mark.asyncio
async def test_ui2_id_collision(tmp_path):
    db_path = str(tmp_path / "test_ui2.db")
    repo = SQLiteProxyRepository(db_path=db_path)
    await repo.initialize()
    
    p1 = ProxyConfig(raw_url="vless://...", protocol="vless", remark="Proxy1")
    p1.group_name = "OldGroup"
    await repo.save(p1)
    
    r1 = RawXrayConfig(name="Raw1", raw_payload='{"a":1}', source_type="import", group_name="OldGroup")
    await repo.save_raw_config(r1)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    assert len(proxies) == 1
    assert len(raws) == 1
    assert proxies[0].id == 1
    assert raws[0].id == 1
    
    tools = ToolsManager(repo)
    
    finished_called = asyncio.Event()
    def on_finished(action, count):
        finished_called.set()
        
    tools.action_finished.connect(on_finished)
    
    proxy_ids = [1]
    raw_ids = [1]
    tools.execute_move(proxy_ids, raw_ids, "NewGroup")
    await asyncio.wait_for(finished_called.wait(), timeout=2.0)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    assert proxies[0].group_name == "NewGroup"
    assert raws[0].group_name == "NewGroup"
    
    finished_called.clear()
    
    tools.execute_move([], [1], "RawOnlyGroup")
    await asyncio.wait_for(finished_called.wait(), timeout=2.0)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    assert proxies[0].group_name == "NewGroup"
    assert raws[0].group_name == "RawOnlyGroup"
    
    finished_called.clear()
    
    tools.execute_delete([1], [], action_type="delete")
    await asyncio.wait_for(finished_called.wait(), timeout=2.0)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    assert len(proxies) == 0
    assert len(raws) == 1
    
    finished_called.clear()
    
    p2 = ProxyConfig(raw_url="vless://...", protocol="vless", remark="Proxy2")
    p2.group_name = "NewGroup"
    await repo.save(p2)
    proxies = await repo.get_all()
    assert len(proxies) == 1
    
    tools.execute_delete([proxies[0].id], [raws[0].id], action_type="delete")
    await asyncio.wait_for(finished_called.wait(), timeout=2.0)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    assert len(proxies) == 0
    assert len(raws) == 0

