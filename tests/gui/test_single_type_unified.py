import pytest
import asyncio

from domain.models.proxy import ProxyConfig
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

import gui.tabs.archive.managers.tools_manager
gui.tabs.archive.managers.tools_manager.AsyncTaskWorker = MockAsyncTaskWorker

async def create_repo(tmp_path):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_single.db"))
    await repo.initialize()
    p = ProxyConfig(raw_url="vmess://", protocol="vmess", remark="P1")
    p.group_name = "OldGroup"
    await repo.save(p)
    r = RawXrayConfig(name="R1", raw_payload="{}", group_name="OldGroup")
    await repo.save_raw_config(r)
    return repo

@pytest.mark.asyncio
async def test_proxy_only_move(tmp_path):
    repo = await create_repo(tmp_path)
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    tools = ToolsManager(repo)
    
    tools.execute_move([proxies[0].id], [], "NewGroup")
    await asyncio.sleep(0.05)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    assert proxies_after[0].group_name == "NewGroup"
    assert raws_after[0].group_name == "OldGroup"

@pytest.mark.asyncio
async def test_raw_only_move(tmp_path):
    repo = await create_repo(tmp_path)
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    tools = ToolsManager(repo)
    
    tools.execute_move([], [raws[0].id], "NewGroup")
    await asyncio.sleep(0.05)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    assert proxies_after[0].group_name == "OldGroup"
    assert raws_after[0].group_name == "NewGroup"

@pytest.mark.asyncio
async def test_proxy_only_delete(tmp_path):
    repo = await create_repo(tmp_path)
    proxies = await repo.get_all()
    tools = ToolsManager(repo)
    
    tools.execute_delete([proxies[0].id], [])
    await asyncio.sleep(0.05)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    assert len(proxies_after) == 0
    assert len(raws_after) == 1

@pytest.mark.asyncio
async def test_raw_only_delete(tmp_path):
    repo = await create_repo(tmp_path)
    raws = await repo.get_all_raw_configs()
    tools = ToolsManager(repo)
    
    tools.execute_delete([], [raws[0].id])
    await asyncio.sleep(0.05)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    assert len(proxies_after) == 1
    assert len(raws_after) == 0

@pytest.mark.asyncio
async def test_non_existing_ids(tmp_path):
    repo = await create_repo(tmp_path)
    tools = ToolsManager(repo)
    
    count_called = []
    def on_finished(action, count):
        count_called.append(count)
        
    tools.action_finished.connect(on_finished)
    
    tools.execute_move([999], [888], "NewGroup")
    await asyncio.sleep(0.05)
    
    assert count_called[0] == 2
