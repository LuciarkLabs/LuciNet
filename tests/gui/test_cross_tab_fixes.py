import pytest
import asyncio
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

from domain.models.proxy import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from repository.sqlite_repo import SQLiteProxyRepository
from gui.tabs.connect.tab_main import ConnectTab
from services.core_manager import CoreManager

import sys

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
gui.tabs.connect.tab_main.AsyncTaskWorker = MockAsyncTaskWorker

@pytest.fixture(scope="module")
def qapp():
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app
    except ImportError:
        yield None

from gui.event_bus import event_bus

from gui.event_bus import event_bus

@pytest.fixture(autouse=True, scope="function")
def clear_settings():
    settings = QSettings("LuciNet", "Client")
    settings.clear()
    yield
    settings.clear()

@pytest.fixture
def make_tab():
    tabs = []
    def _make(repo, scan_svc=None):
        if scan_svc is None:
            scan_svc = MagicMock()
        t = ConnectTab(repo, scan_svc)
        tabs.append(t)
        return t
    
    yield _make
    
    for t in tabs:
        try:
            event_bus.proxy_selected.disconnect(t.on_proxy_selected)
        except Exception:
            pass
        try:
            event_bus.request_quick_connect.disconnect(t.handle_quick_connect)
        except Exception:
            pass
        t.deleteLater()

@pytest.mark.asyncio
async def test_connect_tab_proxy_config(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_ct.db"))
    await repo.initialize()
    
    tab = make_tab(repo)
    
    p = ProxyConfig(raw_url="vmess://", protocol="vmess", remark="Test Proxy", server="1.1.1.1", port=443)
    p.id = 1
    
    tab.on_proxy_selected(p)
    assert tab.ui.lbl_selected_node.text() == "Test Proxy"
    assert tab.settings.value("last_selected_type") == "proxy"
    assert int(tab.settings.value("last_selected_id")) == 1

@pytest.mark.asyncio
async def test_connect_tab_raw_config(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_ct2.db"))
    await repo.initialize()
    
    tab = make_tab(repo)
    
    r = RawXrayConfig(name="Raw Config 1", raw_payload="{}")
    r.id = 5
    
    tab.on_proxy_selected(r)
    assert tab.ui.lbl_selected_node.text() == "Raw Config 1"
    assert tab.settings.value("last_selected_type") == "raw"
    assert int(tab.settings.value("last_selected_id")) == 5
    
@pytest.mark.asyncio
async def test_id_collision_restore(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_collision.db"))
    await repo.initialize()
    
    p = ProxyConfig(raw_url="vmess://", protocol="vmess", remark="Collision Proxy")
    await repo.save(p)
    p = (await repo.get_all())[0]
    
    r = RawXrayConfig(name="Collision Raw", raw_payload="{}")
    await repo.save_raw_config(r)
    
    settings = QSettings("LuciNet", "Client")
    settings.clear()
    settings.setValue("last_selected_type", "raw")
    settings.setValue("last_selected_id", str(r.id))
    
    tab = make_tab(repo)
    
    await asyncio.sleep(0.1)
    
    assert tab.selected_proxy is not None
    assert isinstance(tab.selected_proxy, RawXrayConfig)
    assert tab.selected_proxy.name == "Collision Raw"

@pytest.mark.asyncio
async def test_legacy_restore(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_legacy.db"))
    await repo.initialize()
    
    p = ProxyConfig(raw_url="vmess://", protocol="vmess", remark="Legacy Proxy")
    await repo.save(p)
    proxies = await repo.get_all()
    p = proxies[0]
    
    settings = QSettings("LuciNet", "Client")
    settings.clear()
    settings.setValue("last_proxy_id", str(p.id))
    
    tab = make_tab(repo)
    
    await asyncio.sleep(0.1)
    
    assert tab.selected_proxy is not None
    assert isinstance(tab.selected_proxy, ProxyConfig)
    assert tab.selected_proxy.remark == "Legacy Proxy"

@pytest.mark.asyncio
async def test_core_manager_stop(tmp_path):
    cm = CoreManager()
    cm.process = MagicMock()
    cm.process.state.return_value = 2
    
    with patch("subprocess.run") as mock_run:
        cm.stop_connection(clear_sys_proxy=False)
        cm.process.kill.assert_called_once()
        cm.process.waitForFinished.assert_called_once()
        
        for call in mock_run.call_args_list:
            args = call[0][0]
            assert "taskkill" not in args

from gui.event_bus import event_bus

@pytest.mark.asyncio
async def test_event_bus_proxy_selected(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_eb.db"))
    await repo.initialize()
    tab = make_tab(repo)

    r = RawXrayConfig(name="EventBus Raw", raw_payload='{"test": 1}')
    r.id = 10

    assert tab.selected_proxy is None

    event_bus.proxy_selected.emit(r)
    await asyncio.sleep(0.05)

    assert tab.selected_proxy is not None
    assert isinstance(tab.selected_proxy, RawXrayConfig)
    assert tab.selected_proxy.name == "EventBus Raw"
    assert tab.ui.lbl_selected_node.text() == "EventBus Raw"


@pytest.mark.asyncio
async def test_event_bus_quick_connect(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_eb_qc.db"))
    await repo.initialize()
    tab = make_tab(repo)

    r = RawXrayConfig(name="QuickConnect Raw", raw_payload='{"test": 2}')
    r.id = 20

    with patch.object(tab.core_manager, "start_connection") as mock_start:
        event_bus.request_quick_connect.emit(r)
        await asyncio.sleep(0.05)

        assert tab.selected_proxy is not None
        assert isinstance(tab.selected_proxy, RawXrayConfig)
        assert tab.selected_proxy.name == "QuickConnect Raw"
        
        mock_start.assert_called_once()
        args, kwargs = mock_start.call_args
        assert kwargs["proxy"] is r
        assert isinstance(kwargs["proxy"], RawXrayConfig)


@pytest.mark.asyncio
async def test_quick_connect_while_connected(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_qc_running.db"))
    await repo.initialize()
    tab = make_tab(repo)

    r = RawXrayConfig(name="New Raw Config", raw_payload='{"test": 3}')
    r.id = 30

    tab.core_manager.is_connected = True
    
    def side_effect_stop(*args, **kwargs): tab.core_manager.is_connected = False
    with patch.object(tab.core_manager, "stop_connection", side_effect=side_effect_stop) as mock_stop,          patch.object(tab.core_manager, "start_connection") as mock_start:
         
        event_bus.request_quick_connect.emit(r)
        await asyncio.sleep(0.05)

        mock_stop.assert_called_once()
        mock_start.assert_called_once()
        
        args, kwargs = mock_start.call_args
        assert kwargs["proxy"] is r
        assert isinstance(kwargs["proxy"], RawXrayConfig)


@pytest.mark.asyncio
async def test_invalid_last_selected_type(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_invalid.db"))
    await repo.initialize()
    
    settings = QSettings("LuciNet", "Client")
    settings.setValue("last_selected_type", "garbage")
    settings.setValue("last_selected_id", "1")
    
    tab = make_tab(repo)
    await asyncio.sleep(0.05)
    
    assert tab.selected_proxy is None

@pytest.mark.asyncio
async def test_quick_connect_disconnected_proxy(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_qc1.db"))
    await repo.initialize()
    tab = make_tab(repo)

    p = ProxyConfig(raw_url="vmess://", protocol="vmess", remark="Proxy1")
    p.id = 1

    tab.core_manager.is_connected = False
    with patch.object(tab.core_manager, "start_connection") as mock_start:
        event_bus.request_quick_connect.emit(p)
        await asyncio.sleep(0.05)
        mock_start.assert_called_once()
        assert kwargs["proxy"] is p if (kwargs := mock_start.call_args[1]) else mock_start.call_args[0][0] is p

@pytest.mark.asyncio
async def test_quick_connect_disconnected_raw(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_qc2.db"))
    await repo.initialize()
    tab = make_tab(repo)

    r = RawXrayConfig(name="Raw1", raw_payload='{}')
    r.id = 2

    tab.core_manager.is_connected = False
    with patch.object(tab.core_manager, "start_connection") as mock_start:
        event_bus.request_quick_connect.emit(r)
        await asyncio.sleep(0.05)
        mock_start.assert_called_once()
        assert kwargs["proxy"] is r if (kwargs := mock_start.call_args[1]) else mock_start.call_args[0][0] is r

@pytest.mark.asyncio
async def test_quick_connect_connected_proxy_to_raw(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_qc3.db"))
    await repo.initialize()
    tab = make_tab(repo)

    r = RawXrayConfig(name="RawNew", raw_payload='{}')
    r.id = 3

    tab.core_manager.is_connected = True
    
    def side_effect_stop(*args, **kwargs):
        tab.core_manager.is_connected = False
        
    with patch.object(tab.core_manager, "stop_connection", side_effect=side_effect_stop) as mock_stop,          patch.object(tab.core_manager, "start_connection") as mock_start:
        event_bus.request_quick_connect.emit(r)
        await asyncio.sleep(0.05)
        
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
        assert kwargs["proxy"] is r if (kwargs := mock_start.call_args[1]) else mock_start.call_args[0][0] is r

@pytest.mark.asyncio
async def test_quick_connect_connected_raw_to_proxy(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_qc4.db"))
    await repo.initialize()
    tab = make_tab(repo)

    p = ProxyConfig(raw_url="vmess://", protocol="vmess", remark="ProxyNew")
    p.id = 4

    tab.core_manager.is_connected = True
    
    def side_effect_stop(*args, **kwargs):
        tab.core_manager.is_connected = False
        
    with patch.object(tab.core_manager, "stop_connection", side_effect=side_effect_stop) as mock_stop,          patch.object(tab.core_manager, "start_connection") as mock_start:
        event_bus.request_quick_connect.emit(p)
        await asyncio.sleep(0.05)
        
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
        assert kwargs["proxy"] is p if (kwargs := mock_start.call_args[1]) else mock_start.call_args[0][0] is p

@pytest.mark.asyncio
async def test_quick_connect_stop_exception(qapp, tmp_path, make_tab):
    repo = SQLiteProxyRepository(db_path=str(tmp_path / "test_qc_exc.db"))
    await repo.initialize()
    tab = make_tab(repo)

    r = RawXrayConfig(name="RawExc", raw_payload='{}')
    r.id = 55
    
    old_proxy = ProxyConfig(remark="Old", protocol="vmess", raw_url="vmess://")
    tab.selected_proxy = old_proxy

    tab.core_manager.is_connected = True
    
    def side_effect_stop(*args, **kwargs):
        raise RuntimeError("Simulated stop failure")
        
    with patch.object(tab.core_manager, "stop_connection", side_effect=side_effect_stop) as mock_stop,          patch.object(tab.core_manager, "start_connection") as mock_start:
        
        event_bus.request_quick_connect.emit(r)
        await asyncio.sleep(0.05)
        
        mock_stop.assert_called_once()
        mock_start.assert_not_called()
        
        assert tab.selected_proxy is old_proxy
