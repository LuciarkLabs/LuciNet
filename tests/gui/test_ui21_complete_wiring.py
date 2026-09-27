import pytest
from unittest.mock import MagicMock, patch
import asyncio

from domain.proxy import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from repository.sqlite_repo import SQLiteProxyRepository
from gui.tabs.archive.managers.tools_manager import ToolsManager
from gui.tabs.archive.context_menu_handler import ContextMenuHandler
from gui.tabs.archive.tab_main import ArchiveTab

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog, QMenu
import sys

import gui.workers
import gui.tabs.archive.managers.tools_manager
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
                print(f"WORKER ERROR: {e}")
                self.error_signal.emit(str(e))
        asyncio.create_task(run())

gui.workers.AsyncTaskWorker = MockAsyncTaskWorker
gui.tabs.archive.managers.tools_manager.AsyncTaskWorker = MockAsyncTaskWorker

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

@pytest.mark.asyncio
async def test_context_menu_mixed_move_and_delete(qapp, tmp_path):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_ui21.db"))
    await repo.initialize()
    p1 = ProxyConfig(raw_url="vless://...", protocol="vless", remark="Proxy1")
    p1.group_name = "OldGroup"
    await repo.save(p1)
    
    r1 = RawXrayConfig(name="Raw1", raw_payload='{"a":1}', source_type="import", group_name="OldGroup")
    await repo.save_raw_config(r1)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    
    tools = ToolsManager(repo)
    
    mock_model = MagicMock()
    mock_proxy_model = MagicMock()
    
    handler = ContextMenuHandler(None, tools, MagicMock(), mock_model, mock_proxy_model)
    
    finished_called = asyncio.Event()
    def on_finished(action, count):
        finished_called.set()
    def on_error(msg):
        print(f"TOOLS MANAGER ERROR: {msg}")
        finished_called.set()
        
    tools.action_finished.connect(on_finished)
    tools.error_occurred.connect(on_error)

    with patch('gui.tabs.archive.context_menu_handler.QInputDialog.getItem') as mock_get_item:
        mock_get_item.return_value = ("NewGroup", True)
        handler._request_move([proxies[0], raws[0]], ["OldGroup", "NewGroup"])
        
    await asyncio.wait_for(finished_called.wait(), timeout=2.0)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    assert proxies_after[0].group_name == "NewGroup"
    assert raws_after[0].group_name == "NewGroup"
    
    finished_called.clear()
    
    with patch('gui.tabs.archive.context_menu_handler.QMessageBox.question') as mock_question:
        mock_question.return_value = QMessageBox.Yes
        handler._request_delete([proxies_after[0], raws_after[0]])
        
    await asyncio.wait_for(finished_called.wait(), timeout=2.0)
    
    proxies_final = await repo.get_all()
    raws_final = await repo.get_all_raw_configs()
    assert len(proxies_final) == 0
    assert len(raws_final) == 0

@pytest.mark.asyncio
async def test_toolbar_mixed_move(qapp, tmp_path):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_ui21_move.db"))
    await repo.initialize()
    p1 = ProxyConfig(raw_url="vless://...", protocol="vless", remark="Proxy1")
    p1.group_name = "OldGroup"
    await repo.save(p1)
    
    r1 = RawXrayConfig(name="Raw1", raw_payload='{"a":1}', source_type="import", group_name="OldGroup")
    await repo.save_raw_config(r1)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    
    tools = ToolsManager(repo)
    
    tab = ArchiveTab(repo, MagicMock(), MagicMock())
    tools = tab.tools_manager
    
    tab._get_selected_items = MagicMock(return_value=[proxies[0], raws[0]])
    tab._on_tools_action_finished = MagicMock()
    tab.available_groups = ["OldGroup", "NewGroup"]
    
    finished_called = asyncio.Event()
    def on_finished(action, count):
        finished_called.set()
    def on_error(msg):
        print(f"TOOLS MANAGER ERROR: {msg}")
        finished_called.set()
        
    tools.action_finished.connect(on_finished)
    tools.error_occurred.connect(on_error)

    with patch('gui.tabs.archive.tab_main.QInputDialog.getItem') as mock_get_item, \
         patch('gui.tabs.archive.tab_main.QMessageBox.information') as mock_info:
        mock_get_item.return_value = ("NewGroup2", True)
        try:
            tab._menu_action_move()
        except Exception as e:
            print(f"MENU ACTION MOVE ERROR: {e}")
            finished_called.set()
        
    await asyncio.wait_for(finished_called.wait(), timeout=2.0)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    assert proxies_after[0].group_name == "NewGroup2"
    assert raws_after[0].group_name == "NewGroup2"

@pytest.mark.asyncio
async def test_toolbar_mixed_delete_via_cleanup(qapp, tmp_path):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_ui21_cleanup.db"))
    await repo.initialize()
    p1 = ProxyConfig(raw_url="vless://...", protocol="vless", remark="Proxy1")
    p1.status = "Invalid"
    await repo.save(p1)
    
    r1 = RawXrayConfig(name="Raw1", raw_payload='{"a":1}')
    await repo.save_raw_config(r1)
    
    proxies = await repo.get_all()
    raws = await repo.get_all_raw_configs()
    
    tools = ToolsManager(repo)
    tab = ArchiveTab(repo, MagicMock(), MagicMock())
    tools = tab.tools_manager
    
    tools.request_confirmation.connect(tab._handle_tools_confirmation)
    tab._on_tools_action_finished = MagicMock()
    
    finished_called = asyncio.Event()
    def on_finished(action, count):
        finished_called.set()
    def on_error(msg):
        print(f"TOOLS MANAGER ERROR: {msg}")
        finished_called.set()
        
    tools.action_finished.connect(on_finished)
    tools.error_occurred.connect(on_error)
    
    all_items = proxies + raws
    
    with patch('gui.tabs.archive.tab_main.QMessageBox.question') as mock_question, \
         patch('gui.tabs.archive.tab_main.QMessageBox.information') as mock_info:
        mock_question.return_value = QMessageBox.Yes
        tools.prepare_delete_invalid(all_items, None)
        
    await asyncio.wait_for(finished_called.wait(), timeout=2.0)
    
    proxies_after = await repo.get_all()
    raws_after = await repo.get_all_raw_configs()
    assert len(proxies_after) == 0
    assert len(raws_after) == 1
