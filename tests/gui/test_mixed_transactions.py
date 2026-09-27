import pytest
import asyncio
from unittest.mock import patch, MagicMock

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
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_mixed.db"))
    await repo.initialize()
    p = ProxyConfig(raw_url="vmess://", protocol="vmess", remark="P1")
    p.group_name = "OldGroup"
    await repo.save(p)
    r = RawXrayConfig(name="R1", raw_payload="{}", group_name="OldGroup")
    await repo.save_raw_config(r)
    return repo



@pytest.mark.asyncio
async def test_successful_mixed_move(tmp_path):
    repo = await create_repo(tmp_path)
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    
    tools = ToolsManager(repo)
    tools.execute_move([proxies[0].id], [raws[0].id], "NewGroup")
    await asyncio.sleep(0.05)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert proxies_after[0].group_name == "NewGroup"
    assert raws_after[0].group_name == "NewGroup"


@pytest.mark.asyncio
async def test_successful_mixed_delete(tmp_path):
    repo = await create_repo(tmp_path)
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    
    tools = ToolsManager(repo)
    tools.execute_delete([proxies[0].id], [raws[0].id])
    await asyncio.sleep(0.05)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert len(proxies_after) == 0
    assert len(raws_after) == 0


@pytest.mark.asyncio
async def test_atomic_rollback_move_raw_fails(tmp_path):
    repo = await create_repo(tmp_path)
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    
    tools = ToolsManager(repo)
    
    original_executemany = None
    
    def mock_executemany(sql, parameters=None):
        if "UPDATE xray_raw_configs" in sql:
            raise RuntimeError("Injected Raw Failure")
        return original_executemany(sql, parameters)

    import aiosqlite
    original_connect = aiosqlite.connect
    
    class FailingConnection:
        def __init__(self, conn):
            self.conn = conn
            
        async def __aenter__(self):
            self.real_db = await self.conn.__aenter__()
            self.original_execute = self.real_db.execute
            self.original_executemany = self.real_db.executemany
            self.original_commit = self.real_db.commit
            self.original_rollback = self.real_db.rollback
            
            async def executemany_hook(sql, parameters=None):
                if "UPDATE xray_raw_configs" in sql:
                    raise RuntimeError("Injected Failure in Raw")
                return await self.original_executemany(sql, parameters)
                
            self.real_db.executemany = executemany_hook
            return self.real_db
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.conn.__aexit__(exc_type, exc_val, exc_tb)

    def failing_connect(*args, **kwargs):
        conn = original_connect(*args, **kwargs)
        return FailingConnection(conn)
        
    with patch("repository.sqlite_repo.aiosqlite.connect", side_effect=failing_connect):
        tools.execute_move([proxies[0].id], [raws[0].id], "NewGroup")
        await asyncio.sleep(0.05)
        
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert proxies_after[0].group_name == "OldGroup"
    assert raws_after[0].group_name == "OldGroup"


@pytest.mark.asyncio
async def test_atomic_rollback_delete_raw_fails(tmp_path):
    repo = await create_repo(tmp_path)
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    
    tools = ToolsManager(repo)
    
    import aiosqlite
    original_connect = aiosqlite.connect
    
    class FailingConnection:
        def __init__(self, conn):
            self.conn = conn
            
        async def __aenter__(self):
            self.real_db = await self.conn.__aenter__()
            self.original_executemany = self.real_db.executemany
            
            async def executemany_hook(sql, parameters=None):
                if "DELETE FROM xray_raw_configs" in sql:
                    raise RuntimeError("Injected Failure in Raw Delete")
                return await self.original_executemany(sql, parameters)
                
            self.real_db.executemany = executemany_hook
            return self.real_db
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.conn.__aexit__(exc_type, exc_val, exc_tb)

    def failing_connect(*args, **kwargs):
        conn = original_connect(*args, **kwargs)
        return FailingConnection(conn)
        
    with patch("repository.sqlite_repo.aiosqlite.connect", side_effect=failing_connect):
        tools.execute_delete([proxies[0].id], [raws[0].id])
        await asyncio.sleep(0.05)
        
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert len(proxies_after) == 1
    assert len(raws_after) == 1


@pytest.mark.asyncio
async def test_id_collision(tmp_path):
    repo = await create_repo(tmp_path)
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    
    assert proxies[0].id == raws[0].id
    
    tools = ToolsManager(repo)
    tools.execute_move([proxies[0].id], [], "NewGroup")
    await asyncio.sleep(0.05)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    
    assert proxies_after[0].group_name == "NewGroup"
    assert raws_after[0].group_name == "OldGroup"


@pytest.mark.asyncio
async def test_empty_ids(tmp_path):
    repo = await create_repo(tmp_path)
    tools = ToolsManager(repo)
    
    tools.execute_move([], [], "NewGroup")
    tools.execute_delete([], [])
    await asyncio.sleep(0.05)
    
    proxies_after = await repo.get_all()
    assert len(proxies_after) == 1

